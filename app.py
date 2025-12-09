from flask import Flask, request, render_template
import subprocess
import os
import time
import uuid
import shutil

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        if "file" not in request.files:
            return render_template("index.html", error="No file uploaded")
        
        f = request.files["file"]
        
        if f.filename == "":
            return render_template("index.html", error="No file selected")
        
        # Check file extension
        if not f.filename.endswith('.cpp'):
            return render_template("index.html", error="Only .cpp files are allowed")

        # Create temporary folder
        run_id = str(uuid.uuid4())
        temp_dir = f"/tmp/runs/{run_id}"  # Use /tmp in Linux
        os.makedirs(temp_dir, exist_ok=True)

        # Save solution
        cpp_path = f"{temp_dir}/solution.cpp"
        exe_path = f"{temp_dir}/solution"  # No .exe extension for Linux
        out_path = f"{temp_dir}/out.txt"

        f.save(cpp_path)

        # Compile with g++
        compile_res = subprocess.run(
            ["g++", "-std=c++17", "-O2", "-static", cpp_path, "-o", exe_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if compile_res.returncode != 0:
            error_message = compile_res.stderr.replace(cpp_path, "your code")
            return render_template("index.html", error=f"Compilation Error:\n{error_message}")

        # Make executable
        os.chmod(exe_path, 0o755)

        # Run tests
        tests_dir = "tests"
        if not os.path.exists(tests_dir):
            return render_template("index.html", error="Tests directory not found")
        
        tests = sorted([x[:-3] for x in os.listdir(tests_dir) if x.endswith(".in")])
        
        if not tests:
            return render_template("index.html", error="No test cases found")
        
        test_results = []
        passed_count = 0
        total_count = len(tests)

        for t in tests:
            infile = f"tests/{t}.in"
            expected = f"tests/{t}.out"

            try:
                # Clear caches for more consistent timing (Linux specific)
                if os.geteuid() == 0:  # If running as root
                    subprocess.run(["sync"], capture_output=True)
                    with open("/proc/sys/vm/drop_caches", "w") as f:
                        f.write("3")
                
                start = time.perf_counter()  # More precise timing
                with open(infile, 'rb') as fin, open(out_path, "wb") as fout:
                    run_res = subprocess.run(
                        [exe_path],
                        stdin=fin,
                        stdout=fout,
                        stderr=subprocess.PIPE,
                        timeout=2  # 2 seconds TL
                    )
                
                elapsed = time.perf_counter() - start
                
                if run_res.stderr:
                    stderr_msg = run_res.stderr.decode('utf-8', errors='ignore')
                    test_results.append({
                        'name': t,
                        'status': 'RE',
                        'message': f'Runtime Error: {stderr_msg[:100]}',
                        'time': elapsed
                    })
                    continue
                
                # Compare output
                with open(out_path, 'r', encoding='utf-8') as u, open(expected, 'r', encoding='utf-8') as e:
                    user_lines = [line.rstrip('\n').rstrip('\r') for line in u]
                    expected_lines = [line.rstrip('\n').rstrip('\r') for line in e]
                    
                    # Compare ignoring trailing whitespace and empty lines at end
                    user_clean = [line for line in user_lines if line.strip() != ''] or ['']
                    expected_clean = [line for line in expected_lines if line.strip() != ''] or ['']
                    
                    if user_clean == expected_clean:
                        status = "OK"
                        message = f"({elapsed:.3f}s)"
                        passed_count += 1
                    else:
                        status = "WA"
                        # Show first difference
                        for i in range(max(len(user_lines), len(expected_lines))):
                            ul = user_lines[i] if i < len(user_lines) else ""
                            el = expected_lines[i] if i < len(expected_lines) else ""
                            if ul.rstrip() != el.rstrip():
                                message = f"Line {i+1}: expected '{el[:50]}...', got '{ul[:50]}...'"
                                break
                        else:
                            if len(user_lines) != len(expected_lines):
                                message = f"Different line count: {len(user_lines)} vs {len(expected_lines)}"
                            else:
                                message = "Wrong Answer (check whitespace or newlines)"
                        
            except subprocess.TimeoutExpired:
                status = "TLE"
                message = "Time Limit Exceeded (2s)"
                elapsed = 2.0
            except MemoryError:
                status = "MLE"
                message = "Memory Limit Exceeded"
                elapsed = 0
            except Exception as e:
                status = "ER"
                message = f"System Error: {str(e)}"
                elapsed = 0

            test_results.append({
                'name': t,
                'status': status,
                'message': message,
                'time': elapsed
            })

        result = {
            'tests': test_results,
            'passed': passed_count,
            'total': total_count,
            'score': f"{passed_count}/{total_count}",
            'percentage': f"{(passed_count/total_count*100):.1f}%" if total_count > 0 else "0%"
        }

        # Cleanup - remove temp directory
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as e:
            print(f"Cleanup error: {e}")

    return render_template("index.html", result=result)

if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("/tmp/runs", exist_ok=True)
    os.makedirs("tests", exist_ok=True)
    
    # Check if g++ is available
    try:
        gpp_check = subprocess.run(["g++", "--version"], capture_output=True, text=True)
        if gpp_check.returncode != 0:
            raise FileNotFoundError
        print("g++ compiler found")
    except FileNotFoundError:
        print("ERROR: g++ not found. Installing...")
        subprocess.run(["sudo", "apt-get", "update"], capture_output=True)
        subprocess.run(["sudo", "apt-get", "install", "-y", "g++"], capture_output=True)
    
    # Install Flask if not present
    try:
        import flask
    except ImportError:
        print("Installing Flask...")
        subprocess.run(["pip3", "install", "flask"], capture_output=True)
    
    print("\n" + "="*50)
    print("C++ Code Tester Server")
    print("="*50)
    print(f"Server URL: http://localhost:8000")
    print(f"Test directory: {os.path.abspath('tests')}")
    print("\nTo create test cases:")
    print("  mkdir -p tests")
    print("  echo '1 2' > tests/test1.in")
    print("  echo '3' > tests/test1.out")
    print("="*50 + "\n")
    
    app.run(host="0.0.0.0", port=8000, debug=True)