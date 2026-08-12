import subprocess
import glob, os, os.path

##Remove all files

mydir="/Users/rowena/Other Projects/external_data_study/PY/Government/Award Result"

filelist = glob.glob(os.path.join(mydir, "*.json"))
for f in filelist:
    os.remove(f)


os.chdir('/Users/rowena/Other Projects/external_data_study/PY/Government/Award Result')

result = subprocess.run(
        ["python3", "epd.py"],
        # input=t,
        # text=True,
        capture_output=True
    )

result = subprocess.run(
        ["python3", "dsd.py"],
        # input=t,
        # text=True,
        capture_output=True
    )

result = subprocess.run(
        ["python3", "cedd.py"],
        # input=t,
        # text=True,
        capture_output=True
    )

result = subprocess.run(
        ["python3", "cedd_consultant.py"],
        # input=t,
        # text=True,
        capture_output=True
    )

result = subprocess.run(
        ["python3", "emsd_award.py"],
        # input=t,
        # text=True,
        capture_output=True
    )

result = subprocess.run(
        ["python3", "emsd_award_construction.py"],
        # input=t,
        # text=True,
        capture_output=True
    )

result = subprocess.run(
        ["python3", "hkaa.py"],
        # input=t,
        # text=True,
        capture_output=True
    )

result = subprocess.run(
        ["python3", "hyd.py"],
        # input=t,
        # text=True,
        capture_output=True
)
    
result = subprocess.run(
        ["python3", "wsd.py"],
        # input=t,
        # text=True,
        capture_output=True
    )

result = subprocess.run(
        ["python3", "wsd_consultant.py"],
        # input=t,
        # text=True,
        capture_output=True
    )

result = subprocess.run(
        ["python3", "td.py"],
        # input=t,
        # text=True,
        capture_output=True
    )

result = subprocess.run(
        ["python3", "gld.py"],
        # input=t,
        # text=True,
        capture_output=True
    )