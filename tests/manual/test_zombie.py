import os
def is_running(pid):
    try:
        os.kill(pid, 0)
        # Check if zombie
        with open(f"/proc/{pid}/stat", "r") as f:
            stat = f.read().split()
            if stat[2] == 'Z':
                return False
        return True
    except:
        return False
print("Done")
