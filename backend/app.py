from flask import Flask, request, jsonify
import os
import traceback
from huggingface_hub import InferenceClient
from huggingface_hub.utils import HfHubHTTPError
from codecarbon import EmissionsTracker
import tempfile
import sys
import subprocess
import time
import statistics
import psutil
import platform
import re
import logging

# Optional: GPU detection
try:
    import GPUtil
except ImportError:
    GPUtil = None

# dotenv to load .env file
from dotenv import load_dotenv
load_dotenv()  # <-- loads HF_TOKEN from .env

# Logging
logging.getLogger("codecarbon").setLevel(logging.INFO)

# ====================== Flask App ======================
app = Flask(__name__)

HF_TOKEN = os.getenv("HF_TOKEN")
MODEL = "Qwen/Qwen3-Coder-30B-A3B-Instruct"

# Initialize Hugging Face client only if token is available
if HF_TOKEN:
    client = InferenceClient(model=MODEL, token=HF_TOKEN, headers={"Accept-Encoding": "identity"})
else:
    client = None
    print("Warning: HF_TOKEN not set. Set it in your .env file.")

# ====================== Helper Functions ======================
def clean_code(code: str) -> str:
    if not code:
        return ""
    for fence in ["```python", "```c", "```cpp", "```java", "```js", "```"]:
        code = code.replace(fence, "")
    code = re.sub(r"\*\*.*?\*\*", "", code)
    code = re.sub(r"^\s*\d+\..*$", "", code, flags=re.MULTILINE)
    code_lines = [
        line for line in code.splitlines()
        if line.strip() and not re.match(r'^\s*Energy|Complexity|Optimizations', line)
    ]
    return "\n".join(code_lines)

def detect_language(code: str, prompt: str = "") -> str:
    code_lower = code.lower()
    if any(kw in code_lower for kw in ["#include", "int main", "printf"]):
        return "c"
    elif "public class" in code_lower:
        return "java"
    elif any(kw in code_lower for kw in ["console.log", "function"]):
        return "javascript"
    elif any(kw in code_lower for kw in ["select", "from", "where"]):
        return "sql"
    elif code.strip() or prompt.strip():
        return "python"
    return "python"

def get_system_wattage():
    cpu_count = psutil.cpu_count(logical=True)
    cpu_power_w = 45
    gpu_power_w = 0
    try:
        if platform.system() == "Windows":
            cpu_power_w = 65
        if GPUtil:
            gpus = GPUtil.getGPUs()
            gpu_power_w = sum([gpu.memoryTotal * 0.5 for gpu in gpus]) if gpus else 0
    except Exception:
        pass
    return cpu_count, cpu_power_w, gpu_power_w

def universal_emissions_tracker(executable, num_runs=3) -> float:
    emissions_list = []
    cpu_count, cpu_power_w, gpu_power_w = get_system_wattage()
    try:
        for _ in range(num_runs):
            start_time = time.time()
            subprocess.run(executable, input="", capture_output=True, text=True, timeout=300)
            elapsed = time.time() - start_time
            energy_kwh = ((cpu_power_w * cpu_count) + gpu_power_w) * elapsed / 3600
            co2_kg = energy_kwh * 0.475
            emissions_list.append(co2_kg)
    except Exception as e:
        print(f"Error in universal tracker: {e}")
        return 0.0
    return statistics.mean(emissions_list) if emissions_list else 0.0

def run_code_and_track_emissions(code: str, test_params: dict, language: str) -> float:
    if not code.strip():
        return 0.0

    temp_file = None
    exec_file = None
    try:
        language = language.lower()
        if language == "python":
            function_name = test_params.get("function_name", "dummy_function")
            data_size = test_params.get("data_size", 1000)
            wrapped_code = f"""
import sys, traceback
from codecarbon import EmissionsTracker
import logging
logging.getLogger("codecarbon").setLevel(logging.INFO)
{code}
tracker = EmissionsTracker(save_to_file=False)
tracker.start()
try:
    func = locals().get('{function_name}')
    if callable(func):
        try:
            func(list(range({data_size})), {data_size}, {data_size}//2)
        except TypeError:
            func()
except Exception as e:
    print("ERROR:", e, file=sys.stderr)
emissions = tracker.stop()
"""
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                temp_file = f.name
                f.write(wrapped_code)
                f.flush()
            executable = [sys.executable, temp_file]
            tracker = EmissionsTracker(save_to_file=False)
            tracker.start()
            subprocess.run(executable, input="", capture_output=True, text=True, timeout=300)
            emissions = tracker.stop()
            return emissions if emissions else 0.0

        elif language in ["c", "cpp"]:
            code = clean_code(code)
            suffix = ".c" if language == "c" else ".cpp"
            with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as f:
                temp_file = f.name
                f.write(code)
                f.flush()
            exec_file = temp_file.replace(suffix, "")
            compile_res = subprocess.run(["gcc", temp_file, "-o", exec_file], capture_output=True, text=True, timeout=120)
            if compile_res.returncode != 0:
                print(f"{language.upper()} compilation failed:", compile_res.stderr)
                return 0.0
            return universal_emissions_tracker([exec_file])
        else:
            return universal_emissions_tracker(["echo", "ok"])
    except Exception as e:
        print(f"Error: {e}\n{traceback.format_exc()}")
        return 0.0
    finally:
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
        if exec_file and os.path.exists(exec_file):
            os.remove(exec_file)

# ====================== Flask Endpoints ======================
@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "pong", "message": "Backend is running"}), 200

@app.route("/codegen", methods=["POST"])
def codegen():
    try:
        data = request.json or {}
        prompt = data.get("prompt", "")
        language_input = data.get("language", "")
        language = detect_language("", prompt) if not language_input else language_input

        if not prompt:
            return jsonify({"error": "No prompt provided"}), 400
        if client is None:
            return jsonify({"error": "Hugging Face API token not set."}), 500

        system_prompt = f"You are a helpful {language} coding assistant. Generate clear, concise, carbon and power efficient short code. Provide only the code block with best case time and space complexity with proper executable format. Do not include any comments or explanations."
        full_prompt = f"Generate a {language} function that {prompt}."

        start_time = time.time()
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": full_prompt}]
        result = client.chat_completion(messages=messages)
        request_time = time.time() - start_time

        if not result.choices or not hasattr(result.choices[0].message, 'content'):
            return jsonify({"error": "Invalid response from Hugging Face model"}), 500

        code = clean_code(result.choices[0].message.content)

        cpu_count, cpu_power_w, gpu_power_w = get_system_wattage()
        energy_kwh = ((cpu_power_w * cpu_count) + gpu_power_w) * request_time / 3600
        llm_co2_kg = energy_kwh * 0.475

        execution_co2_kg = run_code_and_track_emissions(code, {}, language)

        if not code:
            code = f"# No {language} code generated."

        return jsonify({"code": code, "language": language, "llm_co2_kg": llm_co2_kg, "execution_co2_kg": execution_co2_kg, "total_co2_kg": llm_co2_kg + execution_co2_kg})

    except HfHubHTTPError as e:
        return jsonify({"error": f"Hugging Face Hub API error: {str(e)}"}), 500
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@app.route("/optimize", methods=["POST"])
def optimize():
    try:
        data = request.json or {}
        unoptimized_code = data.get("code", "")
        language_input = data.get("language", "")
        language = detect_language(unoptimized_code, "") if not language_input else language_input

        if not unoptimized_code:
            return jsonify({"error": "No code provided for optimization"}), 400
        if client is None:
            return jsonify({"error": "Hugging Face API token not set."}), 500

        test_case_params = {"function_name": "find_first_occurrence", "data_size": 1000000}
        co2_before_kg = run_code_and_track_emissions(unoptimized_code, test_case_params, language)

        optimization_prompt = f"""
The following {language} code is inefficient. Provide an optimized version that reduces energy consumption and CO2 footprint with best-case space and time complexity but without any comments and in proper executable format.
Unoptimized code:
{language} {unoptimized_code}
Provide only the optimized {language} code.
"""
        start_time = time.time()
        messages = [{"role": "system", "content": f"You are a skilled {language} code optimizer. Respond with the optimized code."}, {"role": "user", "content": optimization_prompt}]
        result = client.chat_completion(messages=messages)
        request_time = time.time() - start_time

        if not result.choices or not hasattr(result.choices[0].message, 'content'):
            return jsonify({"error": "Invalid response from Hugging Face model"}), 500

        code_raw = clean_code(result.choices[0].message.content)

        cpu_count, cpu_power_w, gpu_power_w = get_system_wattage()
        energy_kwh = ((cpu_power_w * cpu_count) + gpu_power_w) * request_time / 3600
        llm_co2_kg = energy_kwh * 0.475

        co2_after_kg = run_code_and_track_emissions(code_raw, test_case_params, language)

        return jsonify({"optimized_code": code_raw, "language": language, "before_co2": co2_before_kg, "after_co2": co2_after_kg, "llm_co2_kg": llm_co2_kg})

    except HfHubHTTPError as e:
        return jsonify({"error": f"Hugging Face Hub API error: {str(e)}"}), 500
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
