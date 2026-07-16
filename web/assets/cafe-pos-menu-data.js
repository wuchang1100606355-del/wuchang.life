(function () {
  "use strict";
  window.WUCHANG_QUICKCLICK_MENU = Object.freeze(
{
  "adi": {
    "candidateRefs": [
      "QUICKCLICK:M387676:P_49180031",
      "QUICKCLICK:M387676:P_49180040",
      "QUICKCLICK:M387676:P_49180058",
      "QUICKCLICK:M387676:P_49180065",
      "QUICKCLICK:M387676:P_49180073",
      "QUICKCLICK:M387676:P_49180080",
      "QUICKCLICK:M387676:P_49180083",
      "QUICKCLICK:M387676:P_49180086",
      "QUICKCLICK:M387676:P_49180089",
      "QUICKCLICK:M387676:P_55529588",
      "QUICKCLICK:M387676:P_55531708",
      "QUICKCLICK:M387676:P_49180034",
      "QUICKCLICK:M387676:P_49180048",
      "QUICKCLICK:M387676:P_49180050",
      "QUICKCLICK:M387676:P_49180063",
      "QUICKCLICK:M387676:P_60978237",
      "QUICKCLICK:M387676:P_49180033",
      "QUICKCLICK:M387676:P_49180043",
      "QUICKCLICK:M387676:P_49180057",
      "QUICKCLICK:M387676:P_49180068",
      "QUICKCLICK:M387676:P_54786329",
      "QUICKCLICK:M387676:P_54786336",
      "QUICKCLICK:M387676:P_54786340",
      "QUICKCLICK:M387676:P_60979278",
      "QUICKCLICK:M387676:P_49180039",
      "QUICKCLICK:M387676:P_49180047",
      "QUICKCLICK:M387676:P_49180053",
      "QUICKCLICK:M387676:P_49180061",
      "QUICKCLICK:M387676:P_49180070",
      "QUICKCLICK:M387676:P_49180079",
      "QUICKCLICK:M387676:P_49180081",
      "QUICKCLICK:M387676:P_49180084",
      "QUICKCLICK:M387676:P_49180087",
      "QUICKCLICK:M387676:P_49180090",
      "QUICKCLICK:M387676:P_49180093",
      "QUICKCLICK:M387676:P_49180095",
      "QUICKCLICK:M387676:P_49180038",
      "QUICKCLICK:M387676:P_49180049",
      "QUICKCLICK:M387676:P_49180051",
      "QUICKCLICK:M387676:P_49180062",
      "QUICKCLICK:M387676:P_49180069",
      "QUICKCLICK:M387676:P_49180078",
      "QUICKCLICK:M387676:P_49180082",
      "QUICKCLICK:M387676:P_49180085",
      "QUICKCLICK:M387676:P_49180088",
      "QUICKCLICK:M387676:P_49180092",
      "QUICKCLICK:M387676:P_49180094",
      "QUICKCLICK:M387676:P_60978810",
      "QUICKCLICK:M387676:P_60979277",
      "QUICKCLICK:M387676:P_49180052",
      "QUICKCLICK:M387676:P_49180060",
      "QUICKCLICK:M387676:P_49180036",
      "QUICKCLICK:M387676:P_49180045",
      "QUICKCLICK:M387676:P_49180054",
      "QUICKCLICK:M387676:P_49180067",
      "QUICKCLICK:M387676:P_49180071",
      "QUICKCLICK:M387676:P_49180077",
      "QUICKCLICK:M387676:P_60978239"
    ],
    "contractRefs": {
      "determinismProfileRef": "canonical-source-ref-order:v1",
      "evidenceRef": "sha256:18798f9fe998b68bbe1ff168110ef2521c03404ff0950730b729823e13086109",
      "observationSetRef": "quickclick-active-products:58@sha256:18798f9fe998b68bbe1ff168110ef2521c03404ff0950730b729823e13086109",
      "representationRef": "quickclick-menu:M387676@sha256:18798f9fe998b68bbe1ff168110ef2521c03404ff0950730b729823e13086109",
      "strategyRef": "adi-strategy:pos-menu-demo:v1",
      "verifierRef": "cafe-pos-browser-product:v1"
    },
    "productionState": "HOLD_ADI_NOT_CONFIGURED",
    "publicBoundary": "REF_ONLY",
    "role": "AI_BOUNDED_PRODUCT_REFERENCE_INDEX",
    "state": "DEMO_FIXED_CANDIDATE_ONLY"
  },
  "categories": [
    {
      "id": "coffee",
      "label": "咖啡飲品"
    },
    {
      "id": "tea-other",
      "label": "茶與無咖啡因"
    },
    {
      "id": "food",
      "label": "餐食與點心"
    },
    {
      "id": "beans",
      "label": "咖啡豆"
    },
    {
      "id": "drip",
      "label": "濾掛咖啡"
    }
  ],
  "optionGroups": [
    {
      "id": "O7835309",
      "name": "尺寸(30)+溫度+甜度",
      "questions": [
        {
          "displayName": "尺寸",
          "id": "O7835309:Q1",
          "name": "尺寸",
          "options": [
            {
              "displayName": "L",
              "id": "O7835309:Q1:O1",
              "name": "L(+30)",
              "priceDelta": 30,
              "sourceOptionCode": "QC_OI_26159949"
            },
            {
              "displayName": "M",
              "id": "O7835309:Q1:O2",
              "name": "M(+0)",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159972"
            },
            {
              "displayName": "S",
              "id": "O7835309:Q1:O3",
              "name": "S(-15)",
              "priceDelta": -15,
              "sourceOptionCode": "QC_OI_31851882"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924334"
        },
        {
          "displayName": "溫度",
          "id": "O7835309:Q2",
          "name": "溫度",
          "options": [
            {
              "displayName": "去冰",
              "id": "O7835309:Q2:O1",
              "name": "去冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159950"
            },
            {
              "displayName": "少冰",
              "id": "O7835309:Q2:O2",
              "name": "少冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159951"
            },
            {
              "displayName": "正常冰",
              "id": "O7835309:Q2:O3",
              "name": "正常冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159952"
            },
            {
              "displayName": "溫",
              "id": "O7835309:Q2:O4",
              "name": "溫",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159953"
            },
            {
              "displayName": "熱",
              "id": "O7835309:Q2:O5",
              "name": "熱",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159954"
            },
            {
              "displayName": "微冰",
              "id": "O7835309:Q2:O6",
              "name": "微冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159951"
            },
            {
              "displayName": "冰沙",
              "id": "O7835309:Q2:O7",
              "name": "冰沙",
              "priceDelta": 10,
              "sourceOptionCode": "QC_OI_26159950"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924336"
        },
        {
          "displayName": "甜度",
          "id": "O7835309:Q3",
          "name": "甜度",
          "options": [
            {
              "displayName": "正常100%",
              "id": "O7835309:Q3:O1",
              "name": "正常100%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159948"
            },
            {
              "displayName": "少糖75%",
              "id": "O7835309:Q3:O2",
              "name": "少糖75%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159955"
            },
            {
              "displayName": "半糖50%",
              "id": "O7835309:Q3:O3",
              "name": "半糖50%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159957"
            },
            {
              "displayName": "微糖30%",
              "id": "O7835309:Q3:O4",
              "name": "微糖30%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159958"
            },
            {
              "displayName": "無糖0%",
              "id": "O7835309:Q3:O5",
              "name": "無糖0%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159960"
            },
            {
              "displayName": "多糖120%",
              "id": "O7835309:Q3:O6",
              "name": "多糖120%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159964"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924335"
        }
      ]
    },
    {
      "id": "O7835310",
      "name": "尺寸(35)+溫度+甜度",
      "questions": [
        {
          "displayName": "尺寸",
          "id": "O7835310:Q1",
          "name": "尺寸",
          "options": [
            {
              "displayName": "L",
              "id": "O7835310:Q1:O1",
              "name": "L(+35)",
              "priceDelta": 35,
              "sourceOptionCode": "QC_OI_26159971"
            },
            {
              "displayName": "M",
              "id": "O7835310:Q1:O2",
              "name": "M(+0)",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159972"
            },
            {
              "displayName": "S",
              "id": "O7835310:Q1:O3",
              "name": "S(-15)",
              "priceDelta": -15,
              "sourceOptionCode": "QC_OI_31851882"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924334"
        },
        {
          "displayName": "溫度",
          "id": "O7835310:Q2",
          "name": "溫度",
          "options": [
            {
              "displayName": "去冰",
              "id": "O7835310:Q2:O1",
              "name": "去冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159950"
            },
            {
              "displayName": "少冰",
              "id": "O7835310:Q2:O2",
              "name": "少冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159951"
            },
            {
              "displayName": "正常冰",
              "id": "O7835310:Q2:O3",
              "name": "正常冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159952"
            },
            {
              "displayName": "溫",
              "id": "O7835310:Q2:O4",
              "name": "溫",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159953"
            },
            {
              "displayName": "熱",
              "id": "O7835310:Q2:O5",
              "name": "熱",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159954"
            },
            {
              "displayName": "微冰",
              "id": "O7835310:Q2:O6",
              "name": "微冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159951"
            },
            {
              "displayName": "冰沙",
              "id": "O7835310:Q2:O7",
              "name": "冰沙",
              "priceDelta": 10,
              "sourceOptionCode": "QC_OI_26159950"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924336"
        },
        {
          "displayName": "甜度",
          "id": "O7835310:Q3",
          "name": "甜度",
          "options": [
            {
              "displayName": "正常100%",
              "id": "O7835310:Q3:O1",
              "name": "正常100%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159948"
            },
            {
              "displayName": "少糖75%",
              "id": "O7835310:Q3:O2",
              "name": "少糖75%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159955"
            },
            {
              "displayName": "半糖50%",
              "id": "O7835310:Q3:O3",
              "name": "半糖50%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159957"
            },
            {
              "displayName": "微糖30%",
              "id": "O7835310:Q3:O4",
              "name": "微糖30%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159958"
            },
            {
              "displayName": "無糖0%",
              "id": "O7835310:Q3:O5",
              "name": "無糖0%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159960"
            },
            {
              "displayName": "多糖120%",
              "id": "O7835310:Q3:O6",
              "name": "多糖120%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159964"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924335"
        }
      ]
    },
    {
      "id": "O7835311",
      "name": "尺寸(40)+溫度+甜度",
      "questions": [
        {
          "displayName": "尺寸",
          "id": "O7835311:Q1",
          "name": "尺寸",
          "options": [
            {
              "displayName": "L",
              "id": "O7835311:Q1:O1",
              "name": "L+(40)",
              "priceDelta": 40,
              "sourceOptionCode": "QC_OI_26159959"
            },
            {
              "displayName": "M",
              "id": "O7835311:Q1:O2",
              "name": "M(+0)",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159972"
            },
            {
              "displayName": "S",
              "id": "O7835311:Q1:O3",
              "name": "S(-20)",
              "priceDelta": -20,
              "sourceOptionCode": "QC_OI_31851996"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924334"
        },
        {
          "displayName": "溫度",
          "id": "O7835311:Q2",
          "name": "溫度",
          "options": [
            {
              "displayName": "去冰",
              "id": "O7835311:Q2:O1",
              "name": "去冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159950"
            },
            {
              "displayName": "少冰",
              "id": "O7835311:Q2:O2",
              "name": "少冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159951"
            },
            {
              "displayName": "正常冰",
              "id": "O7835311:Q2:O3",
              "name": "正常冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159952"
            },
            {
              "displayName": "溫",
              "id": "O7835311:Q2:O4",
              "name": "溫",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159953"
            },
            {
              "displayName": "熱",
              "id": "O7835311:Q2:O5",
              "name": "熱",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159954"
            },
            {
              "displayName": "微冰",
              "id": "O7835311:Q2:O6",
              "name": "微冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159951"
            },
            {
              "displayName": "冰沙",
              "id": "O7835311:Q2:O7",
              "name": "冰沙",
              "priceDelta": 10,
              "sourceOptionCode": "QC_OI_26159950"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924336"
        },
        {
          "displayName": "甜度",
          "id": "O7835311:Q3",
          "name": "甜度",
          "options": [
            {
              "displayName": "正常100%",
              "id": "O7835311:Q3:O1",
              "name": "正常100%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159948"
            },
            {
              "displayName": "少糖75%",
              "id": "O7835311:Q3:O2",
              "name": "少糖75%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159955"
            },
            {
              "displayName": "半糖50%",
              "id": "O7835311:Q3:O3",
              "name": "半糖50%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159957"
            },
            {
              "displayName": "微糖30%",
              "id": "O7835311:Q3:O4",
              "name": "微糖30%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159958"
            },
            {
              "displayName": "無糖0%",
              "id": "O7835311:Q3:O5",
              "name": "無糖0%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159960"
            },
            {
              "displayName": "多糖120%",
              "id": "O7835311:Q3:O6",
              "name": "多糖120%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159964"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924335"
        }
      ]
    },
    {
      "id": "O7835312",
      "name": "尺寸(5)+溫度+甜度",
      "questions": [
        {
          "displayName": "尺寸",
          "id": "O7835312:Q1",
          "name": "尺寸",
          "options": [
            {
              "displayName": "L",
              "id": "O7835312:Q1:O1",
              "name": "L(+5)",
              "priceDelta": 5,
              "sourceOptionCode": "QC_OI_26159961"
            },
            {
              "displayName": "M",
              "id": "O7835312:Q1:O2",
              "name": "M(+0)",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159972"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924334"
        },
        {
          "displayName": "溫度",
          "id": "O7835312:Q2",
          "name": "溫度",
          "options": [
            {
              "displayName": "去冰",
              "id": "O7835312:Q2:O1",
              "name": "去冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159950"
            },
            {
              "displayName": "少冰",
              "id": "O7835312:Q2:O2",
              "name": "少冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159951"
            },
            {
              "displayName": "正常冰",
              "id": "O7835312:Q2:O3",
              "name": "正常冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159952"
            },
            {
              "displayName": "溫",
              "id": "O7835312:Q2:O4",
              "name": "溫",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159953"
            },
            {
              "displayName": "熱",
              "id": "O7835312:Q2:O5",
              "name": "熱",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159954"
            },
            {
              "displayName": "微冰",
              "id": "O7835312:Q2:O6",
              "name": "微冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159951"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924336"
        },
        {
          "displayName": "甜度",
          "id": "O7835312:Q3",
          "name": "甜度",
          "options": [
            {
              "displayName": "正常100%",
              "id": "O7835312:Q3:O1",
              "name": "正常100%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159948"
            },
            {
              "displayName": "少糖75%",
              "id": "O7835312:Q3:O2",
              "name": "少糖75%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159955"
            },
            {
              "displayName": "半糖50%",
              "id": "O7835312:Q3:O3",
              "name": "半糖50%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159957"
            },
            {
              "displayName": "微糖30%",
              "id": "O7835312:Q3:O4",
              "name": "微糖30%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159958"
            },
            {
              "displayName": "無糖0%",
              "id": "O7835312:Q3:O5",
              "name": "無糖0%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159960"
            },
            {
              "displayName": "多糖120%",
              "id": "O7835312:Q3:O6",
              "name": "多糖120%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159964"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924335"
        }
      ]
    },
    {
      "id": "O7835313",
      "name": "尺寸(10)+溫度+甜度",
      "questions": [
        {
          "displayName": "尺寸",
          "id": "O7835313:Q1",
          "name": "尺寸",
          "options": [
            {
              "displayName": "L",
              "id": "O7835313:Q1:O1",
              "name": "L(+10)",
              "priceDelta": 10,
              "sourceOptionCode": "QC_OI_26159962"
            },
            {
              "displayName": "M",
              "id": "O7835313:Q1:O2",
              "name": "M(+0)",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159972"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924334"
        },
        {
          "displayName": "溫度",
          "id": "O7835313:Q2",
          "name": "溫度",
          "options": [
            {
              "displayName": "去冰",
              "id": "O7835313:Q2:O1",
              "name": "去冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159950"
            },
            {
              "displayName": "少冰",
              "id": "O7835313:Q2:O2",
              "name": "少冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159951"
            },
            {
              "displayName": "正常冰",
              "id": "O7835313:Q2:O3",
              "name": "正常冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159952"
            },
            {
              "displayName": "溫",
              "id": "O7835313:Q2:O4",
              "name": "溫",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159953"
            },
            {
              "displayName": "熱",
              "id": "O7835313:Q2:O5",
              "name": "熱",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159954"
            },
            {
              "displayName": "微冰",
              "id": "O7835313:Q2:O6",
              "name": "微冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159951"
            },
            {
              "displayName": "冰沙",
              "id": "O7835313:Q2:O7",
              "name": "冰沙",
              "priceDelta": 10,
              "sourceOptionCode": "QC_OI_26159950"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924336"
        },
        {
          "displayName": "甜度",
          "id": "O7835313:Q3",
          "name": "甜度",
          "options": [
            {
              "displayName": "正常100%",
              "id": "O7835313:Q3:O1",
              "name": "正常100%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159948"
            },
            {
              "displayName": "少糖75%",
              "id": "O7835313:Q3:O2",
              "name": "少糖75%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159955"
            },
            {
              "displayName": "半糖50%",
              "id": "O7835313:Q3:O3",
              "name": "半糖50%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159957"
            },
            {
              "displayName": "微糖30%",
              "id": "O7835313:Q3:O4",
              "name": "微糖30%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159958"
            },
            {
              "displayName": "無糖0%",
              "id": "O7835313:Q3:O5",
              "name": "無糖0%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159960"
            },
            {
              "displayName": "多糖120%",
              "id": "O7835313:Q3:O6",
              "name": "多糖120%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159964"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924335"
        }
      ]
    },
    {
      "id": "O7835314",
      "name": "尺寸(15)+溫度+甜度",
      "questions": [
        {
          "displayName": "尺寸",
          "id": "O7835314:Q1",
          "name": "尺寸",
          "options": [
            {
              "displayName": "L",
              "id": "O7835314:Q1:O1",
              "name": "L(+15)",
              "priceDelta": 15,
              "sourceOptionCode": "QC_OI_26159963"
            },
            {
              "displayName": "M",
              "id": "O7835314:Q1:O2",
              "name": "M(+0)",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159972"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924334"
        },
        {
          "displayName": "溫度",
          "id": "O7835314:Q2",
          "name": "溫度",
          "options": [
            {
              "displayName": "去冰",
              "id": "O7835314:Q2:O1",
              "name": "去冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159950"
            },
            {
              "displayName": "少冰",
              "id": "O7835314:Q2:O2",
              "name": "少冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159951"
            },
            {
              "displayName": "正常冰",
              "id": "O7835314:Q2:O3",
              "name": "正常冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159952"
            },
            {
              "displayName": "溫",
              "id": "O7835314:Q2:O4",
              "name": "溫",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159953"
            },
            {
              "displayName": "熱",
              "id": "O7835314:Q2:O5",
              "name": "熱",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159954"
            },
            {
              "displayName": "微冰",
              "id": "O7835314:Q2:O6",
              "name": "微冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159951"
            },
            {
              "displayName": "冰沙",
              "id": "O7835314:Q2:O7",
              "name": "冰沙",
              "priceDelta": 10,
              "sourceOptionCode": "QC_OI_26159950"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924336"
        },
        {
          "displayName": "甜度",
          "id": "O7835314:Q3",
          "name": "甜度",
          "options": [
            {
              "displayName": "正常100%",
              "id": "O7835314:Q3:O1",
              "name": "正常100%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159948"
            },
            {
              "displayName": "少糖75%",
              "id": "O7835314:Q3:O2",
              "name": "少糖75%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159955"
            },
            {
              "displayName": "半糖50%",
              "id": "O7835314:Q3:O3",
              "name": "半糖50%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159957"
            },
            {
              "displayName": "微糖30%",
              "id": "O7835314:Q3:O4",
              "name": "微糖30%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159958"
            },
            {
              "displayName": "無糖0%",
              "id": "O7835314:Q3:O5",
              "name": "無糖0%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159960"
            },
            {
              "displayName": "多糖120%",
              "id": "O7835314:Q3:O6",
              "name": "多糖120%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159964"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924335"
        }
      ]
    },
    {
      "id": "O7835315",
      "name": "貝果口味",
      "questions": [
        {
          "displayName": "口味選擇",
          "id": "O7835315:Q1",
          "name": "貝果口味",
          "options": [
            {
              "displayName": "巧克力",
              "id": "O7835315:Q1:O1",
              "name": "巧克力",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159965"
            },
            {
              "displayName": "花生",
              "id": "O7835315:Q1:O2",
              "name": "花生",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159967"
            },
            {
              "displayName": "原味",
              "id": "O7835315:Q1:O3",
              "name": "原味",
              "priceDelta": -10,
              "sourceOptionCode": "QC_OI_26159966"
            },
            {
              "displayName": "奶酥",
              "id": "O7835315:Q1:O4",
              "name": "奶酥==",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159966"
            },
            {
              "displayName": "火腿起司",
              "id": "O7835315:Q1:O5",
              "name": "火腿起司",
              "priceDelta": 15,
              "sourceOptionCode": "QC_OI_26159966"
            },
            {
              "displayName": "奶油",
              "id": "O7835315:Q1:O6",
              "name": "奶油",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159966"
            },
            {
              "displayName": "培根起司",
              "id": "O7835315:Q1:O7",
              "name": "培根起司",
              "priceDelta": 15,
              "sourceOptionCode": null
            },
            {
              "displayName": "香蒜",
              "id": "O7835315:Q1:O8",
              "name": "香蒜",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_31741737"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924338"
        }
      ]
    },
    {
      "id": "O7835316",
      "name": "尺寸(25)+溫度+甜度",
      "questions": [
        {
          "displayName": "尺寸",
          "id": "O7835316:Q1",
          "name": "尺寸",
          "options": [
            {
              "displayName": "L",
              "id": "O7835316:Q1:O1",
              "name": "L(+25)",
              "priceDelta": 25,
              "sourceOptionCode": "QC_OI_26159970"
            },
            {
              "displayName": "M",
              "id": "O7835316:Q1:O2",
              "name": "M(+0)",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159972"
            },
            {
              "displayName": "S",
              "id": "O7835316:Q1:O3",
              "name": "S(-10)",
              "priceDelta": -10,
              "sourceOptionCode": "QC_OI_31848934"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924334"
        },
        {
          "displayName": "溫度",
          "id": "O7835316:Q2",
          "name": "溫度",
          "options": [
            {
              "displayName": "去冰",
              "id": "O7835316:Q2:O1",
              "name": "去冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159950"
            },
            {
              "displayName": "少冰",
              "id": "O7835316:Q2:O2",
              "name": "少冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159951"
            },
            {
              "displayName": "正常冰",
              "id": "O7835316:Q2:O3",
              "name": "正常冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159952"
            },
            {
              "displayName": "溫",
              "id": "O7835316:Q2:O4",
              "name": "溫",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159953"
            },
            {
              "displayName": "熱",
              "id": "O7835316:Q2:O5",
              "name": "熱",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159954"
            },
            {
              "displayName": "微冰",
              "id": "O7835316:Q2:O6",
              "name": "微冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159951"
            },
            {
              "displayName": "冰沙",
              "id": "O7835316:Q2:O7",
              "name": "冰沙",
              "priceDelta": 10,
              "sourceOptionCode": "QC_OI_26159950"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924336"
        },
        {
          "displayName": "甜度",
          "id": "O7835316:Q3",
          "name": "甜度",
          "options": [
            {
              "displayName": "正常100%",
              "id": "O7835316:Q3:O1",
              "name": "正常100%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159948"
            },
            {
              "displayName": "少糖75%",
              "id": "O7835316:Q3:O2",
              "name": "少糖75%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159955"
            },
            {
              "displayName": "半糖50%",
              "id": "O7835316:Q3:O3",
              "name": "半糖50%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159957"
            },
            {
              "displayName": "微糖30%",
              "id": "O7835316:Q3:O4",
              "name": "微糖30%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159958"
            },
            {
              "displayName": "無糖0%",
              "id": "O7835316:Q3:O5",
              "name": "無糖0%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159960"
            },
            {
              "displayName": "多糖120%",
              "id": "O7835316:Q3:O6",
              "name": "多糖120%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159964"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924335"
        }
      ]
    },
    {
      "id": "O7835317",
      "name": "黃金曼特寧+耶加雪夫",
      "questions": [
        {
          "displayName": "磅數",
          "id": "O7835317:Q1",
          "name": "磅數",
          "options": [
            {
              "displayName": "一磅",
              "id": "O7835317:Q1:O1",
              "name": "一磅+400",
              "priceDelta": 400,
              "sourceOptionCode": "QC_OI_26159969"
            },
            {
              "displayName": "半磅",
              "id": "O7835317:Q1:O2",
              "name": "半磅+0",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159973"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924337"
        }
      ]
    },
    {
      "id": "O7835318",
      "name": "曼特寧+藍山",
      "questions": [
        {
          "displayName": "磅數",
          "id": "O7835318:Q1",
          "name": "磅數",
          "options": [
            {
              "displayName": "半磅",
              "id": "O7835318:Q1:O1",
              "name": "半磅+0",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159973"
            },
            {
              "displayName": "一磅",
              "id": "O7835318:Q1:O2",
              "name": "一磅+270",
              "priceDelta": 270,
              "sourceOptionCode": "QC_OI_26159974"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924337"
        }
      ]
    },
    {
      "id": "O7835319",
      "name": "曼巴",
      "questions": [
        {
          "displayName": "磅數",
          "id": "O7835319:Q1",
          "name": "磅數",
          "options": [
            {
              "displayName": "半磅",
              "id": "O7835319:Q1:O1",
              "name": "半磅+0",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159973"
            },
            {
              "displayName": "一磅",
              "id": "O7835319:Q1:O2",
              "name": "一磅+260",
              "priceDelta": 260,
              "sourceOptionCode": "QC_OI_26159975"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924337"
        }
      ]
    },
    {
      "id": "O7835320",
      "name": "招牌咖啡豆",
      "questions": [
        {
          "displayName": "磅數",
          "id": "O7835320:Q1",
          "name": "磅數",
          "options": [
            {
              "displayName": "半磅",
              "id": "O7835320:Q1:O1",
              "name": "半磅+0",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159973"
            },
            {
              "displayName": "一磅",
              "id": "O7835320:Q1:O2",
              "name": "一磅+230",
              "priceDelta": 230,
              "sourceOptionCode": "QC_OI_26159976"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924337"
        }
      ]
    },
    {
      "id": "O7835321",
      "name": "尺寸(40)+糖漿口味+溫度+甜度",
      "questions": [
        {
          "displayName": "尺寸",
          "id": "O7835321:Q1",
          "name": "尺寸",
          "options": [
            {
              "displayName": "L",
              "id": "O7835321:Q1:O1",
              "name": "L(+35)",
              "priceDelta": 35,
              "sourceOptionCode": "QC_OI_26159971"
            },
            {
              "displayName": "M",
              "id": "O7835321:Q1:O2",
              "name": "M(+0)",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159972"
            },
            {
              "displayName": "S",
              "id": "O7835321:Q1:O3",
              "name": "S(-20)",
              "priceDelta": -20,
              "sourceOptionCode": "QC_OI_31851996"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924334"
        },
        {
          "displayName": "溫度",
          "id": "O7835321:Q2",
          "name": "溫度",
          "options": [
            {
              "displayName": "去冰",
              "id": "O7835321:Q2:O1",
              "name": "去冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159950"
            },
            {
              "displayName": "少冰",
              "id": "O7835321:Q2:O2",
              "name": "少冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159951"
            },
            {
              "displayName": "正常冰",
              "id": "O7835321:Q2:O3",
              "name": "正常冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159952"
            },
            {
              "displayName": "溫",
              "id": "O7835321:Q2:O4",
              "name": "溫",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159953"
            },
            {
              "displayName": "熱",
              "id": "O7835321:Q2:O5",
              "name": "熱",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159954"
            },
            {
              "displayName": "微冰",
              "id": "O7835321:Q2:O6",
              "name": "微冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159951"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924336"
        },
        {
          "displayName": "甜度",
          "id": "O7835321:Q3",
          "name": "甜度",
          "options": [
            {
              "displayName": "正常100%",
              "id": "O7835321:Q3:O1",
              "name": "正常100%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159948"
            },
            {
              "displayName": "少糖75%",
              "id": "O7835321:Q3:O2",
              "name": "少糖75%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159955"
            },
            {
              "displayName": "半糖50%",
              "id": "O7835321:Q3:O3",
              "name": "半糖50%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159957"
            },
            {
              "displayName": "微糖30%",
              "id": "O7835321:Q3:O4",
              "name": "微糖30%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159958"
            },
            {
              "displayName": "無糖0%",
              "id": "O7835321:Q3:O5",
              "name": "無糖0%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159960"
            },
            {
              "displayName": "多糖120%",
              "id": "O7835321:Q3:O6",
              "name": "多糖120%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159964"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924335"
        },
        {
          "displayName": "糖漿(+0)",
          "id": "O7835321:Q4",
          "name": "糖漿(+0)",
          "options": [
            {
              "displayName": "榛果",
              "id": "O7835321:Q4:O1",
              "name": "榛果",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159977"
            },
            {
              "displayName": "香草",
              "id": "O7835321:Q4:O2",
              "name": "香草",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159978"
            },
            {
              "displayName": "黑糖",
              "id": "O7835321:Q4:O3",
              "name": "黑糖",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159979"
            },
            {
              "displayName": "焦糖",
              "id": "O7835321:Q4:O4",
              "name": "焦糖",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159980"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924340"
        }
      ]
    },
    {
      "id": "O7835325",
      "name": "尺寸(20)+溫度+甜度",
      "questions": [
        {
          "displayName": "尺寸",
          "id": "O7835325:Q1",
          "name": "尺寸",
          "options": [
            {
              "displayName": "M",
              "id": "O7835325:Q1:O1",
              "name": "M(+0)",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159972"
            },
            {
              "displayName": "L",
              "id": "O7835325:Q1:O2",
              "name": "L(+20)",
              "priceDelta": 20,
              "sourceOptionCode": "QC_OI_26159970"
            },
            {
              "displayName": "S",
              "id": "O7835325:Q1:O3",
              "name": "S(-15)",
              "priceDelta": -15,
              "sourceOptionCode": "QC_OI_31851882"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924334"
        },
        {
          "displayName": "溫度",
          "id": "O7835325:Q2",
          "name": "溫度",
          "options": [
            {
              "displayName": "去冰",
              "id": "O7835325:Q2:O1",
              "name": "去冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159950"
            },
            {
              "displayName": "少冰",
              "id": "O7835325:Q2:O2",
              "name": "少冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159951"
            },
            {
              "displayName": "正常冰",
              "id": "O7835325:Q2:O3",
              "name": "正常冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159952"
            },
            {
              "displayName": "溫",
              "id": "O7835325:Q2:O4",
              "name": "溫",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159953"
            },
            {
              "displayName": "熱",
              "id": "O7835325:Q2:O5",
              "name": "熱",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159954"
            },
            {
              "displayName": "微冰",
              "id": "O7835325:Q2:O6",
              "name": "微冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159951"
            },
            {
              "displayName": "冰沙",
              "id": "O7835325:Q2:O7",
              "name": "冰沙",
              "priceDelta": 10,
              "sourceOptionCode": "QC_OI_26159950"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924336"
        },
        {
          "displayName": "甜度",
          "id": "O7835325:Q3",
          "name": "甜度",
          "options": [
            {
              "displayName": "正常100%",
              "id": "O7835325:Q3:O1",
              "name": "正常100%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159948"
            },
            {
              "displayName": "少糖75%",
              "id": "O7835325:Q3:O2",
              "name": "少糖75%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159955"
            },
            {
              "displayName": "半糖50%",
              "id": "O7835325:Q3:O3",
              "name": "半糖50%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159957"
            },
            {
              "displayName": "微糖30%",
              "id": "O7835325:Q3:O4",
              "name": "微糖30%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159958"
            },
            {
              "displayName": "無糖0%",
              "id": "O7835325:Q3:O5",
              "name": "無糖0%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159960"
            },
            {
              "displayName": "多糖120%",
              "id": "O7835325:Q3:O6",
              "name": "多糖120%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159964"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924335"
        }
      ]
    },
    {
      "id": "O7835326",
      "name": "厚片口味",
      "questions": [
        {
          "displayName": "厚片口味",
          "id": "O7835326:Q1",
          "name": "厚片口味",
          "options": [
            {
              "displayName": "花生",
              "id": "O7835326:Q1:O1",
              "name": "花生",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_31741719"
            },
            {
              "displayName": "巧克力",
              "id": "O7835326:Q1:O2",
              "name": "巧克力",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_31741720"
            },
            {
              "displayName": "奶油",
              "id": "O7835326:Q1:O3",
              "name": "奶油",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_31741721"
            },
            {
              "displayName": "香蒜",
              "id": "O7835326:Q1:O4",
              "name": "香蒜",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_31741737"
            },
            {
              "displayName": "奶酥",
              "id": "O7835326:Q1:O5",
              "name": "奶酥",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159966"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_8497256"
        }
      ]
    },
    {
      "id": "O7835329",
      "name": "簡餐飲品",
      "questions": [
        {
          "displayName": "加購飲品",
          "id": "O7835329:Q1",
          "name": "加購飲品",
          "options": [
            {
              "displayName": "錫蘭紅茶",
              "id": "O7835329:Q1:O1",
              "name": "錫蘭紅茶",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_31741735"
            },
            {
              "displayName": "茉莉綠茶",
              "id": "O7835329:Q1:O2",
              "name": "茉莉綠茶",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_31741736"
            },
            {
              "displayName": "附餐飲料",
              "id": "O7835329:Q1:O3",
              "name": "無須飲品",
              "priceDelta": -20,
              "sourceOptionCode": null
            },
            {
              "displayName": "拿鐵Latte coffee",
              "id": "O7835329:Q1:O4",
              "name": "拿鐵咖啡",
              "priceDelta": 60,
              "sourceOptionCode": null
            },
            {
              "displayName": "定食飲品",
              "id": "O7835329:Q1:O5",
              "name": "卡布奇諾",
              "priceDelta": 60,
              "sourceOptionCode": null
            },
            {
              "displayName": "黑咖啡black coffee",
              "id": "O7835329:Q1:O6",
              "name": "美式咖啡",
              "priceDelta": 40,
              "sourceOptionCode": null
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_8497260"
        }
      ]
    },
    {
      "id": "O8536132",
      "name": "特調加購",
      "questions": [
        {
          "displayName": "尺寸",
          "id": "O8536132:Q1",
          "name": "尺寸",
          "options": [
            {
              "displayName": "L",
              "id": "O8536132:Q1:O1",
              "name": "L(+30)",
              "priceDelta": 30,
              "sourceOptionCode": "QC_OI_26159949"
            },
            {
              "displayName": "M",
              "id": "O8536132:Q1:O2",
              "name": "M(+0)",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159972"
            },
            {
              "displayName": "S",
              "id": "O8536132:Q1:O3",
              "name": "S(-10)",
              "priceDelta": -10,
              "sourceOptionCode": "QC_OI_31848934"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924334"
        },
        {
          "displayName": "溫度",
          "id": "O8536132:Q2",
          "name": "溫度",
          "options": [
            {
              "displayName": "去冰",
              "id": "O8536132:Q2:O1",
              "name": "去冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159950"
            },
            {
              "displayName": "少冰",
              "id": "O8536132:Q2:O2",
              "name": "少冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159951"
            },
            {
              "displayName": "正常冰",
              "id": "O8536132:Q2:O3",
              "name": "正常冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159952"
            },
            {
              "displayName": "溫",
              "id": "O8536132:Q2:O4",
              "name": "溫",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159953"
            },
            {
              "displayName": "熱",
              "id": "O8536132:Q2:O5",
              "name": "熱",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159954"
            },
            {
              "displayName": "微冰",
              "id": "O8536132:Q2:O6",
              "name": "微冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159951"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924336"
        },
        {
          "displayName": "甜度",
          "id": "O8536132:Q3",
          "name": "甜度",
          "options": [
            {
              "displayName": "正常100%",
              "id": "O8536132:Q3:O1",
              "name": "正常100%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159948"
            },
            {
              "displayName": "少糖75%",
              "id": "O8536132:Q3:O2",
              "name": "少糖75%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159955"
            },
            {
              "displayName": "半糖50%",
              "id": "O8536132:Q3:O3",
              "name": "半糖50%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159957"
            },
            {
              "displayName": "微糖30%",
              "id": "O8536132:Q3:O4",
              "name": "微糖30%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159958"
            },
            {
              "displayName": "無糖0%",
              "id": "O8536132:Q3:O5",
              "name": "無糖0%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159960"
            },
            {
              "displayName": "多糖120%",
              "id": "O8536132:Q3:O6",
              "name": "多糖120%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159964"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924335"
        }
      ]
    },
    {
      "id": "O8640678",
      "name": "手沖溫控方式",
      "questions": [
        {
          "displayName": "手沖咖啡溫度",
          "id": "O8640678:Q1",
          "name": "手沖溫度",
          "options": [
            {
              "displayName": "無冰瞬間冷卻",
              "id": "O8640678:Q1:O1",
              "name": "無冰瞬冷",
              "priceDelta": 15,
              "sourceOptionCode": null
            },
            {
              "displayName": "隔水保熱",
              "id": "O8640678:Q1:O2",
              "name": "熱水保溫",
              "priceDelta": 0,
              "sourceOptionCode": null
            },
            {
              "displayName": "無須調整(熱)_",
              "id": "O8640678:Q1:O3",
              "name": "無須調整(熱)",
              "priceDelta": 0,
              "sourceOptionCode": null
            },
            {
              "displayName": "雙層紙杯(限外帶)",
              "id": "O8640678:Q1:O4",
              "name": "外帶雙層紙杯",
              "priceDelta": 3,
              "sourceOptionCode": null
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": null
        }
      ]
    },
    {
      "id": "O8701672",
      "name": "定食飲料",
      "questions": [
        {
          "displayName": "加購飲品",
          "id": "O8701672:Q1",
          "name": "加購飲品",
          "options": [
            {
              "displayName": "錫蘭紅茶",
              "id": "O8701672:Q1:O1",
              "name": "錫蘭紅茶",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_31741735"
            },
            {
              "displayName": "茉莉綠茶",
              "id": "O8701672:Q1:O2",
              "name": "茉莉綠茶",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_31741736"
            },
            {
              "displayName": "附餐飲料",
              "id": "O8701672:Q1:O3",
              "name": "無須飲品",
              "priceDelta": -20,
              "sourceOptionCode": null
            },
            {
              "displayName": "拿鐵Latte coffee",
              "id": "O8701672:Q1:O4",
              "name": "拿鐵咖啡",
              "priceDelta": 60,
              "sourceOptionCode": null
            },
            {
              "displayName": "定食飲品",
              "id": "O8701672:Q1:O5",
              "name": "卡布奇諾",
              "priceDelta": 60,
              "sourceOptionCode": null
            },
            {
              "displayName": "黑咖啡black coffee",
              "id": "O8701672:Q1:O6",
              "name": "美式咖啡",
              "priceDelta": 40,
              "sourceOptionCode": null
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_8497260"
        }
      ]
    },
    {
      "id": "O8701886",
      "name": "加購鮮奶咖啡",
      "questions": [
        {
          "displayName": "尺寸",
          "id": "O8701886:Q1",
          "name": "尺寸",
          "options": [
            {
              "displayName": "L",
              "id": "O8701886:Q1:O1",
              "name": "L(+25)",
              "priceDelta": 25,
              "sourceOptionCode": "QC_OI_26159970"
            },
            {
              "displayName": "M",
              "id": "O8701886:Q1:O2",
              "name": "M(+0)",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159972"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": null
        },
        {
          "displayName": "溫度",
          "id": "O8701886:Q2",
          "name": "溫度",
          "options": [
            {
              "displayName": "正常冰",
              "id": "O8701886:Q2:O1",
              "name": "正常冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159952"
            },
            {
              "displayName": "熱",
              "id": "O8701886:Q2:O2",
              "name": "熱",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159954"
            },
            {
              "displayName": "微冰",
              "id": "O8701886:Q2:O3",
              "name": "微冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159951"
            },
            {
              "displayName": "冰沙",
              "id": "O8701886:Q2:O4",
              "name": "冰沙",
              "priceDelta": 10,
              "sourceOptionCode": "QC_OI_26159950"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": null
        },
        {
          "displayName": "甜度",
          "id": "O8701886:Q3",
          "name": "甜度",
          "options": [
            {
              "displayName": "正常100%",
              "id": "O8701886:Q3:O1",
              "name": "正常100%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159948"
            },
            {
              "displayName": "少糖75%",
              "id": "O8701886:Q3:O2",
              "name": "少糖75%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159955"
            },
            {
              "displayName": "半糖50%",
              "id": "O8701886:Q3:O3",
              "name": "半糖50%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159957"
            },
            {
              "displayName": "微糖30%",
              "id": "O8701886:Q3:O4",
              "name": "微糖30%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159958"
            },
            {
              "displayName": "無糖0%",
              "id": "O8701886:Q3:O5",
              "name": "無糖0%",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159960"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": null
        }
      ]
    },
    {
      "id": "O8796286",
      "name": "西西里調整項目",
      "questions": [
        {
          "displayName": "尺寸",
          "id": "O8796286:Q1",
          "name": "尺寸",
          "options": [
            {
              "displayName": "L西西里",
              "id": "O8796286:Q1:O1",
              "name": "西西里L",
              "priceDelta": 25,
              "sourceOptionCode": null
            },
            {
              "displayName": "M西西里",
              "id": "O8796286:Q1:O2",
              "name": "西西里M",
              "priceDelta": 0,
              "sourceOptionCode": null
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924334"
        },
        {
          "displayName": "溫度",
          "id": "O8796286:Q2",
          "name": "溫度",
          "options": [
            {
              "displayName": "少冰",
              "id": "O8796286:Q2:O1",
              "name": "少冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159951"
            },
            {
              "displayName": "正常冰",
              "id": "O8796286:Q2:O2",
              "name": "正常冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159952"
            },
            {
              "displayName": "微冰",
              "id": "O8796286:Q2:O3",
              "name": "微冰",
              "priceDelta": 0,
              "sourceOptionCode": "QC_OI_26159951"
            },
            {
              "displayName": "冰沙",
              "id": "O8796286:Q2:O4",
              "name": "冰沙",
              "priceDelta": 10,
              "sourceOptionCode": "QC_OI_26159950"
            }
          ],
          "required": true,
          "selectionMode": "single",
          "sourceQuestionCode": "QC_OG_6924336"
        }
      ]
    }
  ],
  "products": [
    {
      "category": "coffee",
      "id": "P_49180031",
      "name": "招牌咖啡",
      "optionGroupIds": [
        "O7835309"
      ],
      "price": 85,
      "sourceCategory": "義式咖啡",
      "sourceProductCode": "QC_P_39095596",
      "sourceProductId": "49180031",
      "sourceRef": "QUICKCLICK:M387676:P_49180031"
    },
    {
      "category": "coffee",
      "id": "P_49180040",
      "name": "特調咖啡",
      "optionGroupIds": [
        "O8536132"
      ],
      "price": 75,
      "sourceCategory": "義式咖啡",
      "sourceProductCode": "QC_P_39095597",
      "sourceProductId": "49180040",
      "sourceRef": "QUICKCLICK:M387676:P_49180040"
    },
    {
      "category": "coffee",
      "id": "P_49180058",
      "name": "咖啡拿鐵",
      "optionGroupIds": [
        "O7835310"
      ],
      "price": 90,
      "sourceCategory": "義式咖啡",
      "sourceProductCode": "QC_P_39095598",
      "sourceProductId": "49180058",
      "sourceRef": "QUICKCLICK:M387676:P_49180058"
    },
    {
      "category": "coffee",
      "id": "P_49180065",
      "name": "風味拿鐵",
      "optionGroupIds": [
        "O7835321"
      ],
      "price": 105,
      "sourceCategory": "義式咖啡",
      "sourceProductCode": "QC_P_39095603",
      "sourceProductId": "49180065",
      "sourceRef": "QUICKCLICK:M387676:P_49180065"
    },
    {
      "category": "coffee",
      "id": "P_49180073",
      "name": "美式黑咖啡",
      "optionGroupIds": [
        "O7835316"
      ],
      "price": 70,
      "sourceCategory": "義式咖啡",
      "sourceProductCode": "QC_P_39095599",
      "sourceProductId": "49180073",
      "sourceRef": "QUICKCLICK:M387676:P_49180073"
    },
    {
      "category": "coffee",
      "id": "P_49180080",
      "name": "卡布奇諾",
      "optionGroupIds": [
        "O7835310"
      ],
      "price": 90,
      "sourceCategory": "義式咖啡",
      "sourceProductCode": "QC_P_39095600",
      "sourceProductId": "49180080",
      "sourceRef": "QUICKCLICK:M387676:P_49180080"
    },
    {
      "category": "coffee",
      "id": "P_49180083",
      "name": "瑪奇朵",
      "optionGroupIds": [
        "O7835321"
      ],
      "price": 110,
      "sourceCategory": "義式咖啡",
      "sourceProductCode": "QC_P_39095601",
      "sourceProductId": "49180083",
      "sourceRef": "QUICKCLICK:M387676:P_49180083"
    },
    {
      "category": "coffee",
      "id": "P_49180086",
      "name": "愛爾蘭威士忌咖啡",
      "optionGroupIds": [
        "O7835311"
      ],
      "price": 105,
      "sourceCategory": "義式咖啡",
      "sourceProductCode": "QC_P_39095595",
      "sourceProductId": "49180086",
      "sourceRef": "QUICKCLICK:M387676:P_49180086"
    },
    {
      "category": "coffee",
      "id": "P_49180089",
      "name": "摩卡奇諾咖啡",
      "optionGroupIds": [
        "O7835311"
      ],
      "price": 105,
      "sourceCategory": "義式咖啡",
      "sourceProductCode": "QC_P_39095602",
      "sourceProductId": "49180089",
      "sourceRef": "QUICKCLICK:M387676:P_49180089"
    },
    {
      "category": "coffee",
      "id": "P_55529588",
      "name": "岩鹽玫瑰",
      "optionGroupIds": [
        "O7835310"
      ],
      "price": 105,
      "sourceCategory": "義式咖啡",
      "sourceProductCode": null,
      "sourceProductId": "55529588",
      "sourceRef": "QUICKCLICK:M387676:P_55529588"
    },
    {
      "category": "coffee",
      "id": "P_55531708",
      "name": "初戀西西里",
      "optionGroupIds": [
        "O8796286"
      ],
      "price": 90,
      "sourceCategory": "義式咖啡",
      "sourceProductCode": null,
      "sourceProductId": "55531708",
      "sourceRef": "QUICKCLICK:M387676:P_55531708"
    },
    {
      "category": "coffee",
      "id": "P_49180034",
      "name": "耶加雪夫",
      "optionGroupIds": [
        "O8640678"
      ],
      "price": 110,
      "sourceCategory": "單品手沖",
      "sourceProductCode": "QC_P_39095604",
      "sourceProductId": "49180034",
      "sourceRef": "QUICKCLICK:M387676:P_49180034"
    },
    {
      "category": "coffee",
      "id": "P_49180048",
      "name": "藍山風味咖啡",
      "optionGroupIds": [
        "O8640678"
      ],
      "price": 100,
      "sourceCategory": "單品手沖",
      "sourceProductCode": "QC_P_39095619",
      "sourceProductId": "49180048",
      "sourceRef": "QUICKCLICK:M387676:P_49180048"
    },
    {
      "category": "coffee",
      "id": "P_49180050",
      "name": "黃金曼特寧",
      "optionGroupIds": [
        "O8640678"
      ],
      "price": 110,
      "sourceCategory": "單品手沖",
      "sourceProductCode": "QC_P_39095617",
      "sourceProductId": "49180050",
      "sourceRef": "QUICKCLICK:M387676:P_49180050"
    },
    {
      "category": "coffee",
      "id": "P_49180063",
      "name": "曼巴咖啡",
      "optionGroupIds": [
        "O8640678"
      ],
      "price": 100,
      "sourceCategory": "單品手沖",
      "sourceProductCode": "QC_P_39095621",
      "sourceProductId": "49180063",
      "sourceRef": "QUICKCLICK:M387676:P_49180063"
    },
    {
      "category": "coffee",
      "id": "P_60978237",
      "name": "肯亞AA",
      "optionGroupIds": [
        "O7835317"
      ],
      "price": 110,
      "sourceCategory": "單品手沖",
      "sourceProductCode": null,
      "sourceProductId": "60978237",
      "sourceRef": "QUICKCLICK:M387676:P_60978237"
    },
    {
      "category": "food",
      "id": "P_49180033",
      "name": "小沙彌素齋飯",
      "optionGroupIds": [
        "O8701672"
      ],
      "price": 130,
      "sourceCategory": "聊國簡餐",
      "sourceProductCode": "QC_P_49180033",
      "sourceProductId": "49180033",
      "sourceRef": "QUICKCLICK:M387676:P_49180033"
    },
    {
      "category": "food",
      "id": "P_49180043",
      "name": "黑胡椒豬柳飯(辣)",
      "optionGroupIds": [
        "O8701672"
      ],
      "price": 130,
      "sourceCategory": "聊國簡餐",
      "sourceProductCode": "QC_P_49180043",
      "sourceProductId": "49180043",
      "sourceRef": "QUICKCLICK:M387676:P_49180043"
    },
    {
      "category": "food",
      "id": "P_49180057",
      "name": "黑胡椒雞柳飯(辣)",
      "optionGroupIds": [
        "O7835329"
      ],
      "price": 130,
      "sourceCategory": "聊國簡餐",
      "sourceProductCode": "QC_P_49180057",
      "sourceProductId": "49180057",
      "sourceRef": "QUICKCLICK:M387676:P_49180057"
    },
    {
      "category": "food",
      "id": "P_49180068",
      "name": "香草起司雞丁飯",
      "optionGroupIds": [
        "O7835329"
      ],
      "price": 135,
      "sourceCategory": "聊國簡餐",
      "sourceProductCode": "QC_P_49180068",
      "sourceProductId": "49180068",
      "sourceRef": "QUICKCLICK:M387676:P_49180068"
    },
    {
      "category": "food",
      "id": "P_54786329",
      "name": "醬燒牛培根丼飯",
      "optionGroupIds": [
        "O8701672"
      ],
      "price": 230,
      "sourceCategory": "聊國簡餐",
      "sourceProductCode": null,
      "sourceProductId": "54786329",
      "sourceRef": "QUICKCLICK:M387676:P_54786329"
    },
    {
      "category": "food",
      "id": "P_54786336",
      "name": "醬燒無骨雞腿飯",
      "optionGroupIds": [
        "O8701672"
      ],
      "price": 230,
      "sourceCategory": "聊國簡餐",
      "sourceProductCode": null,
      "sourceProductId": "54786336",
      "sourceRef": "QUICKCLICK:M387676:P_54786336"
    },
    {
      "category": "food",
      "id": "P_54786340",
      "name": "醬燒松阪豬肉丼飯",
      "optionGroupIds": [
        "O8701672"
      ],
      "price": 235,
      "sourceCategory": "聊國簡餐",
      "sourceProductCode": null,
      "sourceProductId": "54786340",
      "sourceRef": "QUICKCLICK:M387676:P_54786340"
    },
    {
      "category": "food",
      "id": "P_60979278",
      "name": "黑胡椒牛柳飯(辣)",
      "optionGroupIds": [
        "O7835329"
      ],
      "price": 135,
      "sourceCategory": "聊國簡餐",
      "sourceProductCode": null,
      "sourceProductId": "60979278",
      "sourceRef": "QUICKCLICK:M387676:P_60979278"
    },
    {
      "category": "tea-other",
      "id": "P_49180039",
      "name": "錫蘭紅茶🔴",
      "optionGroupIds": [
        "O7835312"
      ],
      "price": 45,
      "sourceCategory": "茶",
      "sourceProductCode": "QC_P_39095620",
      "sourceProductId": "49180039",
      "sourceRef": "QUICKCLICK:M387676:P_49180039"
    },
    {
      "category": "tea-other",
      "id": "P_49180047",
      "name": "錫蘭奶茶🔴",
      "optionGroupIds": [
        "O7835313"
      ],
      "price": 50,
      "sourceCategory": "茶",
      "sourceProductCode": "QC_P_39095610",
      "sourceProductId": "49180047",
      "sourceRef": "QUICKCLICK:M387676:P_49180047"
    },
    {
      "category": "tea-other",
      "id": "P_49180053",
      "name": "錫蘭鮮奶茶🔴🐄",
      "optionGroupIds": [
        "O7835314"
      ],
      "price": 65,
      "sourceCategory": "茶",
      "sourceProductCode": "QC_P_39095608",
      "sourceProductId": "49180053",
      "sourceRef": "QUICKCLICK:M387676:P_49180053"
    },
    {
      "category": "tea-other",
      "id": "P_49180061",
      "name": "錫蘭奶蓋🔴🥛🧈",
      "optionGroupIds": [
        "O7835325"
      ],
      "price": 65,
      "sourceCategory": "茶",
      "sourceProductCode": "QC_P_49180061",
      "sourceProductId": "49180061",
      "sourceRef": "QUICKCLICK:M387676:P_49180061"
    },
    {
      "category": "tea-other",
      "id": "P_49180070",
      "name": "茉莉綠茶🟢",
      "optionGroupIds": [
        "O7835312"
      ],
      "price": 45,
      "sourceCategory": "茶",
      "sourceProductCode": "QC_P_39095606",
      "sourceProductId": "49180070",
      "sourceRef": "QUICKCLICK:M387676:P_49180070"
    },
    {
      "category": "tea-other",
      "id": "P_49180079",
      "name": "茉莉奶茶🟢",
      "optionGroupIds": [
        "O7835313"
      ],
      "price": 50,
      "sourceCategory": "茶",
      "sourceProductCode": "QC_P_39095609",
      "sourceProductId": "49180079",
      "sourceRef": "QUICKCLICK:M387676:P_49180079"
    },
    {
      "category": "tea-other",
      "id": "P_49180081",
      "name": "茉莉鮮奶茶🟢🐄",
      "optionGroupIds": [
        "O7835314"
      ],
      "price": 65,
      "sourceCategory": "茶",
      "sourceProductCode": "QC_P_39095607",
      "sourceProductId": "49180081",
      "sourceRef": "QUICKCLICK:M387676:P_49180081"
    },
    {
      "category": "tea-other",
      "id": "P_49180084",
      "name": "茉莉奶蓋🟢🥛🧈",
      "optionGroupIds": [
        "O7835325"
      ],
      "price": 65,
      "sourceCategory": "茶",
      "sourceProductCode": "QC_P_49180084",
      "sourceProductId": "49180084",
      "sourceRef": "QUICKCLICK:M387676:P_49180084"
    },
    {
      "category": "tea-other",
      "id": "P_49180087",
      "name": "伯爵紅茶🟤",
      "optionGroupIds": [
        "O7835312"
      ],
      "price": 50,
      "sourceCategory": "茶",
      "sourceProductCode": "QC_P_49180087",
      "sourceProductId": "49180087",
      "sourceRef": "QUICKCLICK:M387676:P_49180087"
    },
    {
      "category": "tea-other",
      "id": "P_49180090",
      "name": "伯爵奶茶🟤",
      "optionGroupIds": [
        "O7835313"
      ],
      "price": 60,
      "sourceCategory": "茶",
      "sourceProductCode": "QC_P_49180090",
      "sourceProductId": "49180090",
      "sourceRef": "QUICKCLICK:M387676:P_49180090"
    },
    {
      "category": "tea-other",
      "id": "P_49180093",
      "name": "伯爵鮮奶茶🟤🐄",
      "optionGroupIds": [
        "O7835314"
      ],
      "price": 70,
      "sourceCategory": "茶",
      "sourceProductCode": "QC_P_49180093",
      "sourceProductId": "49180093",
      "sourceRef": "QUICKCLICK:M387676:P_49180093"
    },
    {
      "category": "tea-other",
      "id": "P_49180095",
      "name": "伯爵奶蓋🟤🥛🧈",
      "optionGroupIds": [
        "O7835325"
      ],
      "price": 70,
      "sourceCategory": "茶",
      "sourceProductCode": "QC_P_49180095",
      "sourceProductId": "49180095",
      "sourceRef": "QUICKCLICK:M387676:P_49180095"
    },
    {
      "category": "tea-other",
      "id": "P_49180038",
      "name": "檸檬汁",
      "optionGroupIds": [
        "O7835313"
      ],
      "price": 50,
      "sourceCategory": "無咖啡因",
      "sourceProductCode": "QC_P_39095611",
      "sourceProductId": "49180038",
      "sourceRef": "QUICKCLICK:M387676:P_49180038"
    },
    {
      "category": "tea-other",
      "id": "P_49180049",
      "name": "話梅檸檬",
      "optionGroupIds": [
        "O7835313"
      ],
      "price": 55,
      "sourceCategory": "無咖啡因",
      "sourceProductCode": "QC_P_39095616",
      "sourceProductId": "49180049",
      "sourceRef": "QUICKCLICK:M387676:P_49180049"
    },
    {
      "category": "tea-other",
      "id": "P_49180051",
      "name": "金桔檸檬",
      "optionGroupIds": [
        "O7835313"
      ],
      "price": 55,
      "sourceCategory": "無咖啡因",
      "sourceProductCode": "QC_P_39095612",
      "sourceProductId": "49180051",
      "sourceRef": "QUICKCLICK:M387676:P_49180051"
    },
    {
      "category": "tea-other",
      "id": "P_49180062",
      "name": "蔓越莓蘋果茶",
      "optionGroupIds": [
        "O7835314"
      ],
      "price": 60,
      "sourceCategory": "無咖啡因",
      "sourceProductCode": "QC_P_39095613",
      "sourceProductId": "49180062",
      "sourceRef": "QUICKCLICK:M387676:P_49180062"
    },
    {
      "category": "tea-other",
      "id": "P_49180069",
      "name": "松露巧克力",
      "optionGroupIds": [
        "O7835314"
      ],
      "price": 60,
      "sourceCategory": "無咖啡因",
      "sourceProductCode": "QC_P_39095614",
      "sourceProductId": "49180069",
      "sourceRef": "QUICKCLICK:M387676:P_49180069"
    },
    {
      "category": "tea-other",
      "id": "P_49180078",
      "name": "鮮奶抹茶",
      "optionGroupIds": [
        "O7835314"
      ],
      "price": 60,
      "sourceCategory": "無咖啡因",
      "sourceProductCode": "QC_P_39095615",
      "sourceProductId": "49180078",
      "sourceRef": "QUICKCLICK:M387676:P_49180078"
    },
    {
      "category": "tea-other",
      "id": "P_49180082",
      "name": "綠茶多多",
      "optionGroupIds": [
        "O7835313"
      ],
      "price": 60,
      "sourceCategory": "無咖啡因",
      "sourceProductCode": "QC_P_49180082",
      "sourceProductId": "49180082",
      "sourceRef": "QUICKCLICK:M387676:P_49180082"
    },
    {
      "category": "tea-other",
      "id": "P_49180085",
      "name": "檸檬多多",
      "optionGroupIds": [
        "O7835313"
      ],
      "price": 60,
      "sourceCategory": "無咖啡因",
      "sourceProductCode": "QC_P_49180085",
      "sourceProductId": "49180085",
      "sourceRef": "QUICKCLICK:M387676:P_49180085"
    },
    {
      "category": "tea-other",
      "id": "P_49180088",
      "name": "金桔多多",
      "optionGroupIds": [
        "O7835313"
      ],
      "price": 65,
      "sourceCategory": "無咖啡因",
      "sourceProductCode": "QC_P_49180088",
      "sourceProductId": "49180088",
      "sourceRef": "QUICKCLICK:M387676:P_49180088"
    },
    {
      "category": "tea-other",
      "id": "P_49180092",
      "name": "蔓越莓多多",
      "optionGroupIds": [
        "O7835314"
      ],
      "price": 65,
      "sourceCategory": "無咖啡因",
      "sourceProductCode": "QC_P_49180092",
      "sourceProductId": "49180092",
      "sourceRef": "QUICKCLICK:M387676:P_49180092"
    },
    {
      "category": "tea-other",
      "id": "P_49180094",
      "name": "蒸氣牛奶",
      "optionGroupIds": [
        "O7835314"
      ],
      "price": 60,
      "sourceCategory": "無咖啡因",
      "sourceProductCode": "QC_P_39095618",
      "sourceProductId": "49180094",
      "sourceRef": "QUICKCLICK:M387676:P_49180094"
    },
    {
      "category": "tea-other",
      "id": "P_60978810",
      "name": "仲夏海鹽檸檬",
      "optionGroupIds": [
        "O7835314"
      ],
      "price": 65,
      "sourceCategory": "無咖啡因",
      "sourceProductCode": null,
      "sourceProductId": "60978810",
      "sourceRef": "QUICKCLICK:M387676:P_60978810"
    },
    {
      "category": "tea-other",
      "id": "P_60979277",
      "name": "百香戀乳",
      "optionGroupIds": [
        "O7835314"
      ],
      "price": 70,
      "sourceCategory": "無咖啡因",
      "sourceProductCode": null,
      "sourceProductId": "60979277",
      "sourceRef": "QUICKCLICK:M387676:P_60979277"
    },
    {
      "category": "food",
      "id": "P_49180052",
      "name": "貝果",
      "optionGroupIds": [
        "O7835315"
      ],
      "price": 50,
      "sourceCategory": "點心",
      "sourceProductCode": "QC_P_39095623",
      "sourceProductId": "49180052",
      "sourceRef": "QUICKCLICK:M387676:P_49180052"
    },
    {
      "category": "food",
      "id": "P_49180060",
      "name": "厚片",
      "optionGroupIds": [
        "O7835326"
      ],
      "price": 45,
      "sourceCategory": "點心",
      "sourceProductCode": "QC_P_49180060",
      "sourceProductId": "49180060",
      "sourceRef": "QUICKCLICK:M387676:P_49180060"
    },
    {
      "category": "beans",
      "id": "P_49180036",
      "name": "耶加雪夫",
      "optionGroupIds": [
        "O7835317"
      ],
      "price": 445,
      "sourceCategory": "咖啡豆",
      "sourceProductCode": "QC_P_39095624",
      "sourceProductId": "49180036",
      "sourceRef": "QUICKCLICK:M387676:P_49180036"
    },
    {
      "category": "beans",
      "id": "P_49180045",
      "name": "黃金曼特寧",
      "optionGroupIds": [
        "O7835317"
      ],
      "price": 480,
      "sourceCategory": "咖啡豆",
      "sourceProductCode": "QC_P_39095625",
      "sourceProductId": "49180045",
      "sourceRef": "QUICKCLICK:M387676:P_49180045"
    },
    {
      "category": "beans",
      "id": "P_49180054",
      "name": "精選曼巴",
      "optionGroupIds": [
        "O7835319"
      ],
      "price": 280,
      "sourceCategory": "咖啡豆",
      "sourceProductCode": "QC_P_39095626",
      "sourceProductId": "49180054",
      "sourceRef": "QUICKCLICK:M387676:P_49180054"
    },
    {
      "category": "beans",
      "id": "P_49180067",
      "name": "精品藍山風味咖啡",
      "optionGroupIds": [
        "O7835318"
      ],
      "price": 290,
      "sourceCategory": "咖啡豆",
      "sourceProductCode": "QC_P_39095637",
      "sourceProductId": "49180067",
      "sourceRef": "QUICKCLICK:M387676:P_49180067"
    },
    {
      "category": "beans",
      "id": "P_49180071",
      "name": "招牌咖啡豆",
      "optionGroupIds": [
        "O7835320"
      ],
      "price": 250,
      "sourceCategory": "咖啡豆",
      "sourceProductCode": "QC_P_39095627",
      "sourceProductId": "49180071",
      "sourceRef": "QUICKCLICK:M387676:P_49180071"
    },
    {
      "category": "beans",
      "id": "P_49180077",
      "name": "曼特寧",
      "optionGroupIds": [
        "O7835318"
      ],
      "price": 280,
      "sourceCategory": "咖啡豆",
      "sourceProductCode": "QC_P_39095629",
      "sourceProductId": "49180077",
      "sourceRef": "QUICKCLICK:M387676:P_49180077"
    },
    {
      "category": "beans",
      "id": "P_60978239",
      "name": "肯亞AA",
      "optionGroupIds": [
        "O8640678"
      ],
      "price": 445,
      "sourceCategory": "咖啡豆",
      "sourceProductCode": null,
      "sourceProductId": "60978239",
      "sourceRef": "QUICKCLICK:M387676:P_60978239"
    }
  ],
  "schema": "w7tp.quickclick_menu_web.v1",
  "source": {
    "activeProductCount": 58,
    "authorityState": "VERIFIED_CLOUD_EXPORT_WITH_SOURCE_WARNINGS",
    "excludedProductCount": 6,
    "excludedSourceCategories": [
      "濾掛咖啡"
    ],
    "id": "M387676",
    "modifiedAt": "2025-10-23T02:38:18.000Z",
    "name": "聊閣社區咖啡重新店-QC",
    "normalizedOptionCount": 212,
    "optionGroupCount": 21,
    "rawOptionRowCount": 242,
    "sha256": "18798f9fe998b68bbe1ff168110ef2521c03404ff0950730b729823e13086109",
    "sourceProductCount": 64,
    "sourceWarningCount": 20
  },
  "surfaces": {
    "ai": {
      "llmExecution": "USER_DEVICE_ONLY",
      "productionState": "HOLD_ADI_NOT_CONFIGURED",
      "serverLlm": false,
      "state": "DEMO_FIXED_CANDIDATE_ONLY",
      "system": "ADI"
    },
    "convergence": {
      "state": "L3_CANDIDATE_HUMAN_D8_REQUIRED",
      "system": "TOTAL_FIELD_RECTIFIER"
    },
    "human": {
      "formalPosState": "HOLD_RUNTIME_POS_ORDER_RELEASE_REQUIRED",
      "state": "ODOO_IMPORT_PREVIEW_ONLY",
      "system": "ODOO"
    }
  }
}
  );
}());
