import json
import sys

def run_scan():
    try:
        print("Starting Full System Spatiotemporal Scan...")
        
        # 1. Find or Create Monitor
        Monitor = env['wuchang.ai.hallucination.monitor']
        monitor = Monitor.search([], limit=1)
        if not monitor:
            print("Creating new Hallucination Monitor...")
            try:
                monitor = Monitor.create({}) 
            except Exception as e:
                print(f"Create failed, trying with name: {e}")
                monitor = Monitor.create({'name': 'System Scanner'})
        
        # 2. Trigger Scan
        print(f"Triggering scan on Monitor ID: {monitor.id}")
        monitor.action_build_system_index()
        
        # 3. Verify Result
        monitor.invalidate_recordset() # Refresh
        index_json = monitor.system_structure_index
        if index_json:
            data = json.loads(index_json)
            models_count = len(data.get('system_structure', {}))
            spatial_count = len(data.get('spatiotemporal_index', {}))
            print(f"Scan Complete!")
            print(f" - Indexed Models: {models_count}")
            print(f" - Spatiotemporal Entities: {spatial_count}")
            print(f" - Generated At: {data.get('meta', {}).get('generated_at')}")
        else:
            print("Error: Index is empty after scan!")
        
        env.cr.commit()
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

run_scan()
