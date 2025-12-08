from flask import Flask, request, render_template_string
import subprocess
import os
import time
import uuid

app = Flask(__name__)

HTML = """
<h1>Local C++ Judge</h1>
<form method="POST" enctype="multipart/form-data">
  <input type="file" name="file">
  <button type="submit">Upload & Run</button>
</form>

{% if result %}
<pre>{{ result }}</pre>
{% endif %}
"""

@app.route("/", methods=["GET", "POST"])
def index():
    result = ""
    if request.method == "POST":
        f = request.files["file"]

        # creează folder temporar
        run_id = str(uuid.uuid4())
        os.makedirs(f"runs/{run_id}", exist_ok=True)

        # salvează soluția
        cpp_path = f"runs/{run_id}/solution.cpp"
        exe_path = f"runs/{run_id}/solution"
        out_path = f"runs/{run_id}/out.txt"

        f.save(cpp_path)

        # compilează
        compile_res = subprocess.run(
            ["g++", "-std=c++17", "-O2", cpp_path, "-o", exe_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if compile_res.returncode != 0:
            return render_template_string(HTML, result="Compilation Error:\n" + compile_res.stderr)

        # rulează pe teste
        tests = sorted([x[:-3] for x in os.listdir("tests") if x.endswith(".in")])
        out = []

        for t in tests:
            infile = f"tests/{t}.in"
            expected = f"tests/{t}.out"

            try:
                start = time.time()
                with open(infile) as fin, open(out_path, "w") as fout:
                    subprocess.run(
                        [exe_path],
                        stdin=fin,
                        stdout=fout,
                        stderr=subprocess.PIPE,
                        timeout=1  # 1 secunda TL
                    )
                elapsed = time.time() - start
            except subprocess.TimeoutExpired:
                out.append(f"Test {t}: TLE")
                continue

            # compara output
            with open(out_path) as u, open(expected) as e:
                if u.read().strip() == e.read().strip():
                    out.append(f"Test {t}: OK ({elapsed:.3f}s)")
                else:
                    out.append(f"Test {t}: WA")

        result = "\n".join(out)

    return render_template_string(HTML, result=result)


if __name__ == "__main__":
    os.makedirs("runs", exist_ok=True)
    app.run(host="0.0.0.0", port=8000, debug=True)
