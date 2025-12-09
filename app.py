from flask import Flask, request, render_template
import subprocess
import os
import time
import uuid

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
        os.makedirs(f"runs/{run_id}", exist_ok=True)

        # Save solution
        cpp_path = f"runs/{run_id}/solution.cpp"
        exe_path = f"runs/{run_id}/solution"
        out_path = f"runs/{run_id}/out.txt"

        f.save(cpp_path)

        # Compile
        compile_res = subprocess.run(
            ["g++", "-std=c++17", "-O2", cpp_path, "-o", exe_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if compile_res.returncode != 0:
            error_message = compile_res.stderr.replace(cpp_path, "your code")
            return render_template("index.html", error=f"Compilation Error:\n{error_message}")

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
                start = time.time()
                with open(infile) as fin, open(out_path, "w") as fout:
                    run_res = subprocess.run(
                        [exe_path],
                        stdin=fin,
                        stdout=fout,
                        stderr=subprocess.PIPE,
                        timeout=2  # 2 seconds TL
                    )
                
                if run_res.stderr:
                    test_results.append({
                        'name': t,
                        'status': 'RE',
                        'message': 'Runtime Error',
                        'time': 0
                    })
                    continue
                    
                elapsed = time.time() - start
                
                # Compare output
                with open(out_path) as u, open(expected) as e:
                    user_output = u.read().strip()
                    expected_output = e.read().strip()
                    
                    if user_output == expected_output:
                        status = "OK"
                        message = f"({elapsed:.3f}s)"
                        passed_count += 1
                    else:
                        status = "WA"
                        message = "Wrong Answer"
                        
            except subprocess.TimeoutExpired:
                status = "TLE"
                message = "Time Limit Exceeded"
                elapsed = 2.0
            except Exception as e:
                status = "ER"
                message = f"Error: {str(e)}"
                elapsed = 0

            test_results.append({
                'name': t,
                'status': status,
                'message': message,
                'time': elapsed if 'elapsed' in locals() else 0
            })

        result = {
            'tests': test_results,
            'passed': passed_count,
            'total': total_count,
            'score': f"{passed_count}/{total_count}"
        }

        # Cleanup
        try:
            os.remove(cpp_path)
            os.remove(exe_path)
            os.remove(out_path)
            os.rmdir(f"runs/{run_id}")
        except:
            pass

    return render_template("index.html", result=result)

if __name__ == "__main__":
    os.makedirs("runs", exist_ok=True)
    app.run(host="0.0.0.0", port=8000, debug=True)