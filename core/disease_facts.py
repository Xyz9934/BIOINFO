from __future__ import annotations

from typing import Any, Dict, List


LOCAL_DISEASE_FACTS: Dict[str, Dict[str, Any]] = {
    "leukemia": {
        "is_genetic": False,
        "code_system": "ICD-10-CM",
        "code_system_oid": "2.16.840.1.113883.6.90",
        "code": "C95.90",
        "symptoms": [
            "Persistent fatigue and weakness",
            "Frequent infections or fever",
            "Easy bruising or bleeding",
            "Bone or joint pain",
            "Swollen lymph nodes, liver, or spleen",
            "Unexplained weight loss and night sweats",
        ],
        "precautions": [
            "Avoid infections with careful hygiene and crowd precautions during low immunity periods",
            "Follow blood count monitoring and medical review regularly",
            "Seek urgent care for fever, bleeding, or breathing difficulty",
            "Maintain adequate nutrition and hydration during therapy",
        ],
        "treatment": [
            "Treatment depends on subtype and may include chemotherapy, targeted therapy, immunotherapy, radiation, or stem cell transplant",
            "Supportive care often includes transfusion support and infection management",
            "A hematology specialist should guide final treatment decisions",
        ],
    },
    "breast cancer": {
        "is_genetic": False,
        "code_system": "ICD-10-CM",
        "code_system_oid": "2.16.840.1.113883.6.90",
        "code": "C50.919",
        "symptoms": [
            "Breast lump or thickened area",
            "Change in breast shape or size",
            "Skin dimpling or redness",
            "Nipple inversion or discharge",
            "Pain may occur but is not always present",
        ],
        "precautions": [
            "Do regular self-awareness checks and recommended screening",
            "Discuss family history and BRCA risk with a clinician",
            "Limit alcohol, maintain healthy weight, and stay active",
        ],
        "treatment": [
            "Common treatment options include surgery, chemotherapy, radiation, hormone therapy, and targeted therapy",
            "Management depends on receptor status, tumor stage, and patient condition",
        ],
    },
    "cystic fibrosis": {
        "is_genetic": True,
        "code_system": "ICD-10-CM",
        "code_system_oid": "2.16.840.1.113883.6.90",
        "code": "E84.9",
        "symptoms": [
            "Persistent cough with thick mucus",
            "Repeated chest infections",
            "Poor weight gain despite appetite",
            "Salty-tasting skin",
            "Digestive and pancreatic problems",
        ],
        "precautions": [
            "Follow airway clearance routines regularly",
            "Avoid respiratory infections and keep vaccinations up to date",
            "Use nutrition plans and enzyme supplementation as prescribed",
            "Regular pulmonary follow-up is important",
        ],
        "treatment": [
            "Treatment can include CFTR modulators, antibiotics, bronchodilators, physiotherapy, pancreatic enzymes, and nutritional support",
            "Long-term care is usually multidisciplinary",
        ],
    },
    "parkinson disease": {
        "is_genetic": False,
        "code_system": "ICD-10-CM",
        "code_system_oid": "2.16.840.1.113883.6.90",
        "code": "G20",
        "symptoms": [
            "Tremor at rest",
            "Slowed movement (bradykinesia)",
            "Muscle rigidity",
            "Postural instability and gait problems",
            "Sleep, mood, and autonomic symptoms may occur",
        ],
        "precautions": [
            "Fall prevention at home is very important",
            "Maintain regular physical activity and physiotherapy",
            "Medication timing should be followed closely",
        ],
        "treatment": [
            "Treatment may include levodopa, dopamine agonists, MAO-B inhibitors, physiotherapy, speech therapy, and in selected cases deep brain stimulation",
        ],
    },
    "alzheimer disease": {
        "is_genetic": False,
        "code_system": "ICD-10-CM",
        "code_system_oid": "2.16.840.1.113883.6.90",
        "code": "G30.9",
        "symptoms": [
            "Progressive memory loss",
            "Difficulty with planning and orientation",
            "Language and judgment problems",
            "Behavioral or personality changes",
        ],
        "precautions": [
            "Create a safe environment and structured routine",
            "Monitor medication use and wandering risk",
            "Support caregivers and early medical review",
        ],
        "treatment": [
            "Treatment focuses on symptom control, supportive care, cognitive support, and approved disease-modifying or symptomatic medicines when appropriate",
        ],
    },
    "sickle cell anemia": {
        "is_genetic": True,
        "code_system": "ICD-10-CM",
        "code_system_oid": "2.16.840.1.113883.6.90",
        "code": "D57.1",
        "symptoms": [
            "Pain crises",
            "Chronic anemia and fatigue",
            "Hand-foot swelling",
            "Frequent infections",
            "Jaundice and delayed growth in some patients",
        ],
        "precautions": [
            "Stay hydrated and avoid extreme temperatures",
            "Prevent infection and keep vaccinations updated",
            "Seek urgent care for chest pain, stroke symptoms, or severe pain",
        ],
        "treatment": [
            "Treatment may include folate support, pain control, hydroxyurea, transfusion programs, and in some cases stem cell transplant or gene-based therapies",
        ],
    },
}


def _normalize(text: str) -> str:
    return text.strip().lower()


def get_disease_facts(query: str, related_diseases: List[str] | None = None) -> Dict[str, Any]:
    normalized = _normalize(query)
    related = related_diseases or []

    for key, value in LOCAL_DISEASE_FACTS.items():
        if key in normalized or normalized in key:
            return value

    for disease in related:
        disease_normalized = _normalize(disease)
        for key, value in LOCAL_DISEASE_FACTS.items():
            if key in disease_normalized or disease_normalized in key:
                return value

    return {
        "is_genetic": None,
        "symptoms": [
            f"No detailed local symptom profile is cached yet for '{query}'.",
            "You can still use the disease summary and gene data above.",
        ],
        "precautions": [
            "Consult a qualified clinician for diagnosis-specific advice.",
            "Add this disease to the local JSON cache later for richer offline details.",
        ],
        "treatment": [
            "No detailed local treatment/care note is cached yet.",
            "Use specialist medical guidance for final treatment decisions.",
        ],
    }
