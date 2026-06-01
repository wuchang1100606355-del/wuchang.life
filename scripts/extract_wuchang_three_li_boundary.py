#!/usr/bin/env python3
import hashlib
import html
import json
from pathlib import Path

import shapefile
from pyproj import Transformer


ROOT = Path("/home/taiji_admin/Taiji_Hub")
BASE = ROOT / "data/geospatial/source_official/ntpc_village_boundary_2024/extracted"
OUT_GEOJSON = ROOT / "data/geospatial/wuchang_community_three_li_official_boundary_2026-05-24.geojson"
OUT_KML = ROOT / "data/geospatial/wuchang_community_three_li_official_boundary_2026-05-24.kml"
OUT_MANIFEST = ROOT / "data/geospatial/wuchang_community_three_li_official_boundary_2026-05-24.manifest.json"
ZIP_PATH = ROOT / "data/geospatial/source_official/ntpc_village_boundary_2024/ntpc_village_boundary.zip"
WANTED = {"五常里", "五順里", "仁忠里"}
ORDER = ["五常里", "五順里", "仁忠里"]


def ring_to_wgs84(points, transformer):
    ring = []
    for x, y in points:
        lon, lat = transformer.transform(x, y)
        ring.append([round(lon, 12), round(lat, 12)])
    if ring and ring[0] != ring[-1]:
        ring.append(ring[0])
    return ring


def kml_coordinates(ring):
    return " ".join(f"{lon},{lat},0" for lon, lat in ring)


def main():
    shp_path = next(BASE.glob("*.shp"))
    reader = shapefile.Reader(str(shp_path), encoding="utf-8")
    transformer = Transformer.from_crs("EPSG:3826", "EPSG:4326", always_xy=True)
    features = []

    for shape_record in reader.iterShapeRecords():
        record = shape_record.record.as_dict()
        if record.get("ADMIT") != "三重區" or record.get("ADMIV") not in WANTED:
            continue

        points = shape_record.shape.points
        parts = list(shape_record.shape.parts) + [len(points)]
        rings = [ring_to_wgs84(points[start:end], transformer) for start, end in zip(parts, parts[1:])]
        features.append({
            "type": "Feature",
            "properties": {
                "name": record.get("ADMIV"),
                "city": "新北市",
                "district": record.get("ADMIT"),
                "admit_id": record.get("ADMIT_ID"),
                "village": record.get("ADMIV"),
                "village_id": record.get("ADMIV_ID"),
                "tm2x": record.get("TM2X"),
                "tm2y": record.get("TM2Y"),
                "source_dataset": "新北市里界圖資",
                "source_agency": "新北市政府民政局",
                "source_url": "https://data.gov.tw/dataset/169927",
                "download_url": "https://data.ntpc.gov.tw/api/datasets/8bbd1aca-752c-4df0-b515-1cfd88b36274/csv/zip",
                "association_information_responsibility": "community_association_public_interest_collection_preservation_research",
                "information_scope": [
                    "human_culture",
                    "hydrology",
                    "geography",
                    "local_culture",
                    "local_history"
                ],
                "governance_note": "社區發展協會對人文、水文、地理、文化、歷史資訊有公益收集、儲存、研究與保護責任；涉及個資、會員位置、精密住址時仍需最小必要、分級權限與 audit。",
                "crs_source": "TWD97 / TM2 zone 121 (EPSG:3826)",
                "crs_output": "WGS84 (EPSG:4326)",
                "boundary_precision": "official_open_data_polygon",
                "created_at": "2026-05-24T00:00:00+08:00"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": rings
            }
        })

    features.sort(key=lambda feature: ORDER.index(feature["properties"]["name"]))
    feature_collection = {
        "type": "FeatureCollection",
        "name": "wuchang_community_three_li_official_boundary",
        "features": features
    }
    OUT_GEOJSON.write_text(json.dumps(feature_collection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    colors = {
        "五常里": "7d00ff00",
        "五順里": "7d00ffff",
        "仁忠里": "7dff9900"
    }
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        '  <Document>',
        '    <name>新北市三重區五常社區三里官方里界</name>',
        '    <description>來源：政府資料開放平臺「新北市里界圖資」，提供機關：新北市政府民政局。範圍：五常里、五順里、仁忠里。五常社區發展協會對人文、水文、地理、文化、歷史資訊有公益收集、儲存、研究與保護責任。</description>'
    ]
    for name, color in colors.items():
        lines.append(f'    <Style id="style_{html.escape(name)}"><LineStyle><color>ff333333</color><width>2</width></LineStyle><PolyStyle><color>{color}</color></PolyStyle></Style>')

    for feature in features:
        props = feature["properties"]
        name = props["name"]
        description = "<br/>".join([
            "行政區：新北市三重區",
            f"里別：{name}",
            f"里代碼：{props['village_id']}",
            "來源：新北市里界圖資 / 新北市政府民政局",
            "授權：政府資料開放授權條款-第1版",
            "協會責任：人文、水文、地理、文化、歷史資訊之公益收集、儲存、研究與保護"
        ])
        lines.extend([
            "    <Placemark>",
            f"      <name>{html.escape(name)}</name>",
            f"      <styleUrl>#style_{html.escape(name)}</styleUrl>",
            f"      <description><![CDATA[{description}]]></description>",
            "      <Polygon><outerBoundaryIs><LinearRing>",
            f"        <coordinates>{kml_coordinates(feature['geometry']['coordinates'][0])}</coordinates>",
            "      </LinearRing></outerBoundaryIs></Polygon>",
            "    </Placemark>"
        ])
    lines.extend(["  </Document>", "</kml>"])
    OUT_KML.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "schema": "taiji.geospatial.official_boundary.v1",
        "status": "official_open_data_polygon_extracted",
        "created_at": "2026-05-24T00:00:00+08:00",
        "scope": "新北市三重區五常里、五順里、仁忠里",
        "source": {
            "dataset": "新北市里界圖資",
            "agency": "新北市政府民政局",
            "dataset_url": "https://data.gov.tw/dataset/169927",
            "download_url": "https://data.ntpc.gov.tw/api/datasets/8bbd1aca-752c-4df0-b515-1cfd88b36274/csv/zip",
            "download_sha256": hashlib.sha256(ZIP_PATH.read_bytes()).hexdigest(),
            "license": "政府資料開放授權條款-第1版"
        },
        "association_information_responsibility": {
            "status": "recognized_public_interest_governance_responsibility",
            "subject": "新北市三重區五常社區發展協會",
            "scope": [
                "人文資訊",
                "水文資訊",
                "地理資訊",
                "文化資訊",
                "歷史資訊"
            ],
            "responsibilities": [
                "收集",
                "儲存",
                "研究",
                "保護",
                "來源留痕",
                "分級授權",
                "audit"
            ],
            "privacy_boundary": "公益地理文化資料可治理保存；涉及個資、會員位置、精密住址或服務紀錄時必須最小必要、分級權限、遮罩與 audit。"
        },
        "outputs": {
            "geojson": str(OUT_GEOJSON.relative_to(ROOT)),
            "kml": str(OUT_KML.relative_to(ROOT))
        },
        "villages": [feature["properties"] for feature in features]
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "features": len(features),
        "geojson": str(OUT_GEOJSON),
        "kml": str(OUT_KML),
        "manifest": str(OUT_MANIFEST)
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
