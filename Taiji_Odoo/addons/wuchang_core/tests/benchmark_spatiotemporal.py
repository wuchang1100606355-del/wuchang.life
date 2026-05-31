import time
import sys
from odoo import env

def run_benchmark():
    try:
        Partner = env['res.partner']
        count = 100
        
        print("Starting Spatiotemporal Benchmark...")
        print(f"Sample Size: {count} records")

        # --- Phase 1: Baseline (Standard) ---
        print("\n[Phase 1: Baseline (Standard)]")
        print("- Simulating operations WITHOUT spatial fields...")
        
        # Write Test
        start_time = time.time()
        created_ids = []
        for i in range(count):
            p = Partner.create({'name': f'Bench_Base_{i}'})
            created_ids.append(p.id)
        
        # Commit manually to ensure DB persistence if needed, but for benchmark memory is fine.
        # However, to measure real DB write, we rely on ORM create.
        
        write_duration = time.time() - start_time
        write_tps = count / write_duration
        print(f"Write Time: {write_duration:.4f}s | Rate: {write_tps:.2f} ops/sec")

        # Read Test
        start_time = time.time()
        partners = Partner.browse(created_ids)
        for p in partners:
            _ = p.name
            # Accessing non-spatial field
        
        read_duration = time.time() - start_time
        read_tps = count / read_duration
        print(f"Read Time:  {read_duration:.4f}s | Rate: {read_tps:.2f} ops/sec")

        # Cleanup Phase 1
        partners.unlink()
        env.cr.commit()

        # --- Phase 2: Spatiotemporal (Spatialized) ---
        print("\n[Phase 2: Spatiotemporal (Spatialized)]")
        print("- Simulating operations WITH spatial fields (Lat/Lng/Alt/UUID)...")
        
        # Write Test
        start_time = time.time()
        created_ids = []
        for i in range(count):
            p = Partner.create({
                'name': f'Bench_Spatial_{i}',
                'spatial_idx_lat': 25.0 + (i*0.001),
                'spatial_idx_lng': 121.0 + (i*0.001),
                'spatial_idx_alt': 10.0,
                'spatial_ref_uuid': f'UUID-{i}'
            })
            created_ids.append(p.id)
            
        write_duration_spatial = time.time() - start_time
        write_tps_spatial = count / write_duration_spatial
        print(f"Write Time: {write_duration_spatial:.4f}s | Rate: {write_tps_spatial:.2f} ops/sec")

        # Read Test
        start_time = time.time()
        partners = Partner.browse(created_ids)
        for p in partners:
            _ = p.name
            _ = p.spatial_idx_lat
            _ = p.spatial_ref_uuid
            # Accessing spatial fields triggers fetch
            
        read_duration_spatial = time.time() - start_time
        read_tps_spatial = count / read_duration_spatial
        print(f"Read Time:  {read_duration_spatial:.4f}s | Rate: {read_tps_spatial:.2f} ops/sec")

        # Indexing Test
        print("\n[Phase 3: Indexing Performance]")
        print("- Measuring full Spatiotemporal Index rebuild time...")
        
        # Use existing mixin logic. 
        # Need to find a record that uses WuchangAiIndexMixin. 
        # Usually it's an abstract mixin, need a concrete model.
        # Assuming 'wuchang.task.force' or 'wuchang.ai.hallucination.monitor' inherits it?
        # Let's search for a model that has 'action_build_system_index'
        
        model_with_index = None
        for model_name, model_obj in env.items():
            if hasattr(model_obj, 'action_build_system_index'):
                # Try to find a record
                rec = model_obj.search([], limit=1)
                if not rec:
                    try:
                        rec = model_obj.create({'name': 'Index Bench'})
                    except:
                        pass
                if rec:
                    model_with_index = rec
                    print(f"Found Indexing Model: {model_name}")
                    break
        
        if model_with_index:
            start_time = time.time()
            model_with_index.action_build_system_index()
            idx_duration = time.time() - start_time
            print(f"Indexing Time: {idx_duration:.4f}s (for full system)")
        else:
            print("Warning: No model found with action_build_system_index method.")

        # Cleanup Phase 2
        partners.unlink()
        env.cr.commit()
        
        # Summary
        print("\n" + "="*40)
        print("PERFORMANCE COMPARISON REPORT")
        print("="*40)
        print(f"{'Metric':<20} | {'Baseline':<10} | {'Spatiotemporal':<15} | {'Diff'}")
        print("-" * 60)
        print(f"{'Write (ops/sec)':<20} | {write_tps:<10.2f} | {write_tps_spatial:<15.2f} | {(write_tps_spatial - write_tps):.2f}")
        print(f"{'Read (ops/sec)':<20} | {read_tps:<10.2f} | {read_tps_spatial:<15.2f} | {(read_tps_spatial - read_tps):.2f}")
        print("="*40)

    except Exception as e:
        print(f"Error: {e}")
        env.cr.rollback()

run_benchmark()
