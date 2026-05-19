import subprocess

def run(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout + result.stderr
    except Exception as e:
        return str(e)

output = ""
output += "=== git status ===\n"
output += run("git status")
output += "=== git remote -v ===\n"
output += run("git remote -v")
output += "=== git log -1 ===\n"
output += run("git log -1")

with open("git_output.txt", "w") as f:
    f.write(output)
