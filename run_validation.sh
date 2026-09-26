#!/usr/bin/env bash
# Count read support, take IGV screenshots, caption them and write the report.
# Usage: ./run_validation.sh   (run from ~/osteosarc_sv/igv; needs the osteo_sv conda env and IGV 2.19.7)
set -euo pipefail
cd "$(dirname "$0")"
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate osteo_sv
IGV_APP=/Applications/IGV_2.19.7.app
PORT=60151

igv_up() { [ "$(printf 'echo\n' | nc -w 5 127.0.0.1 $PORT 2>/dev/null)" = "echo" ]; }

# Close IGV on exit (success or failure), but only if this script opened it;
# an IGV the user already had open is left alone.
STARTED_IGV=0
close_igv() {
    if [ "$STARTED_IGV" = 1 ]; then
        printf 'exit\n' | nc -w 5 127.0.0.1 $PORT > /dev/null 2>&1 || true
        sleep 3
        pkill -f 'igv.args' 2> /dev/null || true
    fi
}
trap close_igv EXIT

echo "1/4 counting read support from the BAMs"
python count_support.py > support_counts_all.tsv

echo "2/4 taking IGV screenshots"
if ! igv_up; then
    STARTED_IGV=1
    # Start on our hg38 genome: IGV's default (mm39 here) is still loading when the port opens,
    # and a command sent then crashes IGV. The Mac launcher drops arguments, so start its Java directly.
    (cd "$IGV_APP/Contents" && jdk-21/bin/java -showversion --module-path=Java/lib -Xmx8g @Java/igv.args \
        -Xdock:name=IGV -Xdock:icon=Resources/IGV_64.png -Dapple.laf.useScreenMenuBar=true \
        $([ -f ~/.igv/java_arguments ] && echo "@$HOME/.igv/java_arguments") \
        --module=org.igv/org.broad.igv.ui.Main -g "$OLDPWD/hg38_osteo.json" > "$OLDPWD/igv_session_T1.log" 2>&1 &)
    for _ in $(seq 1 90); do igv_up && break; sleep 2; done
fi
# Commands go over the batch port one at a time; `IGV -b` can hang on the default genome.
# The port answers before IGV has finished starting, so an empty reply means "retry shortly".
python - "$PORT" <<'EOF'
import socket, sys, time
port = int(sys.argv[1])


def connect():
    s = socket.create_connection(("127.0.0.1", port)); s.settimeout(300)
    return s.makefile("rw")


f = connect()
for c in open("batch_T1.igv").read().splitlines():
    if c == "exit":
        continue
    for attempt in range(10):
        f.write(c + "\n"); f.flush(); r = f.readline().strip()
        if r:
            break
        time.sleep(5); f = connect()
    if r != "OK":
        sys.exit(f"IGV command failed: {c} -> {r or 'no reply'}")
EOF

echo "3/4 adding count captions"
python caption_snapshots.py > /dev/null

echo "4/4 writing the report"
python make_report.py
