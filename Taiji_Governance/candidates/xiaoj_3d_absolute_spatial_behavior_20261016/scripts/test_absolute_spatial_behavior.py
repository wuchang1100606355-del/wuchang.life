from __future__ import annotations
import importlib.util,math,unittest
from pathlib import Path
P=Path(__file__).resolve().parent/"absolute_spatial_behavior.py"
spec=importlib.util.spec_from_file_location("absolute_spatial_behavior",P)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class AbsoluteSpatialBehaviorTests(unittest.TestCase):
    def test_z_axis_is_not_discarded_as_in_2d(self):
        self.assertAlmostEqual(m.distance3((0,0,0),(0,0,12)),12)
        self.assertAlmostEqual(m.distance3((1,2,3),(4,6,15)),13)

    def test_camera_rotated_coordinates_preserve_euclidean_distance(self):
        a=(1.2,2.3,3.4);b=(-0.8,0.5,5.6)
        theta=math.pi/3
        def rot(p):
            x,y,z=p
            return (x*math.cos(theta)+z*math.sin(theta),y,-x*math.sin(theta)+z*math.cos(theta))
        self.assertAlmostEqual(m.distance3(a,b),m.distance3(rot(a),rot(b)),places=12)

    def test_model_scale_affects_actual_absolute_distance(self):
        a=(1,2,3);b=(4,6,15)
        self.assertAlmostEqual(m.distance3(a,b),13)
        self.assertAlmostEqual(m.distance3(tuple(x*2 for x in a),tuple(x*2 for x in b)),26)

    def test_absolute_3d_timeline_not_pixel_projection(self):
        a,b=(0,0,0),(0,0,1)
        da,db=(0,0,0),(0,0,1)
        start=m.sample_pair(a,b,da,db,time_ms=0,duration_ms=650)
        mid=m.sample_pair(a,b,da,db,time_ms=325,duration_ms=650)
        end=m.sample_pair(a,b,da,db,time_ms=650,duration_ms=650)
        self.assertAlmostEqual(start["absolute_distance_3d"],1)
        self.assertAlmostEqual(mid["absolute_distance_3d"],1.5)
        self.assertAlmostEqual(end["absolute_distance_3d"],2)
        self.assertEqual(len(end["xyz_a"]),3)
        self.assertEqual(len(end["xyz_b"]),3)

    def test_no_implicit_relative_percentage_only(self):
        self.assertNotEqual(m.distance3((0,0,0),(0,0,4)),m.distance3((0,0,0),(0,0,5)))

    def test_nonfinite_hold(self):
        for x in (math.nan, math.inf,-math.inf):
            with self.subTest(x=x),self.assertRaisesRegex(m.SpatialHold,"HOLD_NONFINITE_3D_POINT"):
                m.distance3((0,0,0),(x,1,2))

    def test_bad_timeline_hold(self):
        for t,d in ((-1,100),(101,100),(0,0)):
            with self.subTest(t=t,d=d),self.assertRaisesRegex(m.SpatialHold,"HOLD_TIMELINE_INVALID"):
                m.sample_pair((0,0,0),(0,1,0),(0,0,0),(1,1,1),time_ms=t,duration_ms=d)

    def test_weight_outside_range_hold(self):
        for w in (-0.1,1.1,math.nan):
            with self.subTest(w=w),self.assertRaisesRegex(m.SpatialHold,"HOLD_MORPH_WEIGHT_INVALID"):
                m.deform3((0,0,0),(1,2,3),w)

    def test_not_a_two_dimensional_model(self):
        with self.assertRaisesRegex(m.SpatialHold,"HOLD_3D_POINT_REQUIRED"):
            m.distance3((0,0),(1,1))

if __name__=="__main__":unittest.main(verbosity=2)
