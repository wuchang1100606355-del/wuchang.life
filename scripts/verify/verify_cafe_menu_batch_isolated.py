#!/usr/bin/env python3
"""Install and test the menu candidate in an empty, private Docker sandbox."""
import argparse
import json
from pathlib import Path
import subprocess
import time
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--addons-path", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    addons = Path(args.addons_path).resolve()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    assert (addons / "wuchang_cafe_menu_options/tests/test_menu_batch.py").is_file()
    prefix = "w7tp_menu_batch_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    net, pg, odoo = prefix + "_net", prefix + "_pg", prefix + "_odoo"
    used = []
    def call(command, timeout=20, check=True):
        result = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
        if check and result.returncode:
            raise RuntimeError(result.stderr[-700:])
        return result
    def production_state():
        return {name: call(["docker", "inspect", name, "--format", "{{.State.StartedAt}}|{{.RestartCount}}|{{.State.Status}}" ]).stdout.strip()
                for name in ("wuchang_os_odoo_18", "wuchang_os_pg")}
    receipt = {"started_at": datetime.now(timezone.utc).isoformat(),
               "source_path": str(addons), "base_commit": "3c2e5884bc149ffbb02d81fdf288506918fae79e",
               "empty_database": True, "production_data_copied": False,
               "host_ports_published": False, "candidate_only": True,
               "total_field_release": "NOT_RUN", "pass": False}
    receipt["production_before"] = production_state()
    try:
        call(["docker", "network", "create", "--internal", net]); used.append(("network", net))
        call(["docker", "run", "-d", "--name", pg, "--network", net,
              "--memory", "900m", "--cpus", "1", "--tmpfs", "/var/lib/postgresql/data:rw,size=1200m",
              "-e", "POSTGRES_USER=odoo", "-e", "POSTGRES_DB=menu_batch_test",
              "-e", "POSTGRES_PASSWORD=isolated-test-only", "postgres:15"])
        used.append(("container", pg))
        for _ in range(40):
            if call(["docker", "exec", pg, "pg_isready", "-q", "-U", "odoo"], check=False).returncode == 0:
                break
            time.sleep(1)
        else:
            raise RuntimeError("ISOLATED_POSTGRES_NOT_READY")
        command = ["docker", "run", "--rm", "--name", odoo, "--network", net,
                   "--memory", "2600m", "--cpus", "2", "--pids-limit", "350",
                   "--mount", "type=bind,src=" + str(addons) + ",dst=/mnt/extra-addons,readonly",
                   "-e", "HOST=" + pg, "-e", "USER=odoo", "-e", "PASSWORD=isolated-test-only",
                   "odoo:18.0", "odoo", "--addons-path=/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons",
                   "-d", "menu_batch_test", "-i", "wuchang_cafe_menu_options", "--without-demo=all",
                   "--no-http", "--max-cron-threads=0", "--stop-after-init", "--test-enable",
                   "--test-tags", "wuchang_menu_batch", "--log-level=test"]
        used.append(("container", odoo))
        print("EMPTY_PRIVATE_ODOO_INSTALL_AND_TEST_STARTED", flush=True)
        result = call(command, timeout=360, check=False)
        log = result.stdout + result.stderr
        (output / "odoo-install-test.log").write_text(log)
        receipt["exit_code"] = result.returncode
        receipt["test_summary"] = [line for line in log.splitlines()
                                   if "tests" in line and any(word in line for word in ("failed", "passed", "error"))][-10:]
        print("ODOO_EXIT", result.returncode, flush=True)
        print("\n".join(log.splitlines()[-30:]), flush=True)
        receipt["pass"] = (result.returncode == 0 and "0 failed, 0 error(s)" in log
                           and "Starting TestMenuBatch.test_" in log)
    except Exception as exc:
        receipt["error"] = str(exc)
        print(type(exc).__name__, str(exc), flush=True)
    finally:
        cleanup = []
        for kind, name in reversed(used):
            command = ["docker", "rm", "-f", name] if kind == "container" else ["docker", "network", "rm", name]
            result = call(command, check=False)
            absent = call(["docker", kind, "inspect", name], check=False).returncode != 0
            cleanup.append({"kind": kind, "name": name, "removed": absent})
        receipt["cleanup"] = cleanup
        receipt["production_after"] = production_state()
        receipt["production_runtime_unchanged"] = receipt["production_before"] == receipt["production_after"]
        receipt["pass"] = receipt["pass"] and all(item["removed"] for item in cleanup) and receipt["production_runtime_unchanged"]
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        (output / "ISOLATED_ODOO_ACCEPTANCE.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
        print("ISOLATED_ACCEPTANCE", receipt["pass"], flush=True)
    return 0 if receipt["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
