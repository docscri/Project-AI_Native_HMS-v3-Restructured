"""The 12 OPD case-sheet templates, transcribed from the department templates document (v1.0, 9 Oct 2026).
Each section has a title and the prompts printed under it; "note" is the department's extra instruction."""

VERSION = 1

COMMON = {
    "patient": ["Name / Patient ID", "Age / Sex", "Date / Time", "Doctor", "New / Follow-up", "Allergies and reaction"],
    "vitals": ["BP (mmHg)", "Pulse (/min)", "RR (/min)", "Temp", "SpO2 (%)", "Room air / O2", "Weight (kg)", "Height"],
}

RULES = [
    "Enter only information actually documented. Do not insert normal examination findings or turn missing history into a negative finding.",
    "Keep medical conditions, medicines and allergies available in every department.",
    "Keep available test results separate from investigations requested. Preserve laterality, units, dates, medication details and diagnostic uncertainty.",
    "Flag unclear or contradictory information for clinician review. Assessment and treatment must reflect the clinician's stated impression and plan.",
    "For follow-up visits, record interval change, treatment response, adherence, adverse effects and new results.",
]

REPORTS = {"title": "Available reports", "prompts": ["Results and dates"]}
IMPRESSION = {"title": "Provisional diagnosis or impression", "prompts": ["Impression / relevant differentials / severity or complications"]}
MANAGEMENT = {"title": "Management", "prompts": ["Investigations - laboratory", "Investigations - imaging / other tests",
                                                  "Treatment - drug, dose, route, frequency and duration / procedure", "Advice",
                                                  "Review / referral / admission", "Return earlier or urgently if"]}


def sheet(label, title, sections, note=""):
    return {"label": label, "title": title, "sections": sections, "note": note}


TEMPLATES = [
    sheet("General Medicine", "General Medicine and General OPD", [
        {"title": "C/O", "prompts": ["Complaint 1 and duration", "Complaint 2 and duration"]},
        {"title": "History of presenting illness", "prompts": ["Onset, progression, severity and associated symptoms", "Relevant negative history / treatment tried and response"]},
        {"title": "Relevant history", "prompts": ["Past medical / surgical history and current medicines", "Relevant personal / family history and functional impact"]},
        {"title": "O/E", "prompts": ["General condition / pallor / icterus / cyanosis / clubbing / nodes / oedema", "CVS - heart sounds, murmurs and other findings",
                                     "RS - air entry, breath sounds and added sounds", "P/A - tenderness, organomegaly, masses and bowel sounds",
                                     "CNS - mental status and relevant neurological findings", "Other focused examination"]},
        REPORTS, IMPRESSION, MANAGEMENT]),
    sheet("General Surgery", "General Surgery", [
        {"title": "C/O", "prompts": ["Pain / swelling / lump / wound / bleeding and duration"]},
        {"title": "History of presenting illness", "prompts": ["Site, onset, progression and associated symptoms", "Bowel / bladder symptoms, relevant negatives and treatment tried"]},
        {"title": "Relevant history", "prompts": ["Previous operations, dates, complications and anaesthetic problems", "Medical conditions / medicines including blood thinners / last oral intake if relevant"]},
        {"title": "O/E", "prompts": ["General condition / hydration", "Local examination - site, size, skin changes, tenderness and other findings",
                                     "P/A - inspection, palpation, percussion and auscultation", "CVS", "RS", "Other examination - rectal examination only if performed"]},
        REPORTS, IMPRESSION, MANAGEMENT], "Include wound care and dressing instructions when relevant."),
    sheet("Obstetrics", "Obstetrics and Antenatal OPD", [
        {"title": "C/O or purpose of visit", "prompts": ["Routine antenatal review / complaint and duration"]},
        {"title": "Obstetric details", "prompts": ["LMP and reliability / EDD / gestational age in weeks and days", "Dating basis - LMP / ultrasound; gravida / para / abortions / living children"]},
        {"title": "Current pregnancy and relevant history", "prompts": ["Symptoms / bleeding / leaking fluid / pain or contractions / fetal movements if applicable",
                                                                         "Antenatal care and complications / previous pregnancy outcomes and delivery modes",
                                                                         "Previous caesarean or other surgery / medical conditions / medicines and supplements"]},
        {"title": "O/E", "prompts": ["General condition / pallor / oedema; CVS / RS as examined", "P/A - fundal height / lie / presentation / fetal heart rate if assessed",
                                     "Uterine tenderness / contractions / other examination if performed"]},
        REPORTS,
        {"title": "Obstetric assessment", "prompts": ["Impression / relevant differentials / severity or complications"]},
        {"title": "Management", "prompts": ["Investigations / ultrasound", "Treatment / supplements", "Diet / activity / antenatal advice",
                                            "Next antenatal review / delivery planning if discussed", "Urgent review / referral / admission instructions"]}]),
    sheet("Gynaecology", "Gynaecology", [
        {"title": "C/O", "prompts": ["Complaint and duration"]},
        {"title": "History of presenting illness", "prompts": ["Onset, progression, associated symptoms / urinary or bowel symptoms / treatment tried"]},
        {"title": "Menstrual history", "prompts": ["LMP / regularity / interval / duration / flow", "Dysmenorrhoea / abnormal bleeding / menopausal status if applicable"]},
        {"title": "Relevant history", "prompts": ["Obstetric history / pregnancy possibility / contraception / relevant sexual history", "Previous procedures / screening / medical conditions / current medicines"]},
        {"title": "O/E", "prompts": ["General condition / pallor; P/A", "Local / speculum / bimanual findings only if performed",
                                     "Consent / chaperone details if documented; CVS / RS / other systems as examined"]},
        REPORTS, IMPRESSION, MANAGEMENT]),
    sheet("Paediatrics", "Paediatrics", [
        {"title": "Child and informant", "prompts": ["Exact age / informant and relationship / measured weight in kg"]},
        {"title": "C/O", "prompts": ["Complaint and duration, as reported by child or caregiver"]},
        {"title": "History of presenting illness", "prompts": ["Onset, progression and associated symptoms", "Feeding / fluid intake / activity / sleep / urine output / stools", "Medicines already given and response"]},
        {"title": "Relevant history", "prompts": ["Birth / neonatal history / immunisation / development / growth", "Previous illnesses / admissions / medicines / family history / sick contacts"]},
        {"title": "O/E", "prompts": ["Appearance / activity / hydration / growth measurements if assessed", "RS - work of breathing, air entry and breath sounds; CVS",
                                     "P/A / CNS / ENT / skin and other focused findings"]},
        REPORTS, IMPRESSION, MANAGEMENT]),
    sheet("Orthopaedics", "Orthopaedics", [
        {"title": "C/O", "prompts": ["Pain / swelling / restricted movement - site, side and duration"]},
        {"title": "History of presenting illness", "prompts": ["Injury mechanism and date/time / onset of non-traumatic symptoms",
                                                                "Progression / ability to bear weight or use limb / numbness or weakness / treatment tried"]},
        {"title": "Relevant history", "prompts": ["Previous injury / operations / implants / baseline mobility", "Medical conditions and current medicines"]},
        {"title": "O/E", "prompts": ["General condition; local examination - site and side", "Inspection - swelling, deformity and wounds", "Palpation - tenderness, warmth and other findings",
                                     "Range of movement / gait / weight-bearing ability if assessed", "Distal neurovascular findings / special tests / other systems as indicated"]},
        REPORTS, IMPRESSION, MANAGEMENT], "Include immobilisation, weight-bearing instructions and rehabilitation when relevant."),
    sheet("ENT", "ENT", [
        {"title": "C/O", "prompts": ["Ear / nose / throat complaint, duration and side"]},
        {"title": "History of presenting illness", "prompts": ["Onset, progression and associated symptoms", "Hearing / balance / nasal / swallowing / voice symptoms, relevant negatives", "Treatment taken and response"]},
        {"title": "Relevant history", "prompts": ["Previous ENT illness or surgery / exposure / tobacco use", "Relevant medical conditions and current medicines"]},
        {"title": "O/E", "prompts": ["General condition", "Right ear - pinna / canal / tympanic membrane", "Left ear - pinna / canal / tympanic membrane",
                                     "Nose - external nose / septum / mucosa / turbinates / discharge", "Oral cavity / throat / neck / lymph nodes",
                                     "Hearing or vestibular tests / endoscopy if performed; other systems as relevant"]},
        REPORTS, IMPRESSION, MANAGEMENT]),
    sheet("Ophthalmology", "Ophthalmology", [
        {"title": "C/O", "prompts": ["Complaint, duration and right eye / left eye / both eyes"]},
        {"title": "History of presenting illness", "prompts": ["Onset, progression, associated symptoms and visual symptoms", "Trauma / chemical exposure / contact lens use / eye drops used"]},
        {"title": "Relevant history", "prompts": ["Previous eye disease or surgery / spectacles / medical conditions / medicines"]},
        {"title": "O/E for each eye separately", "prompts": ["Visual acuity with correction status - right eye / left eye", "Pupils / eye movements - right eye / left eye",
                                                             "Lids / conjunctiva - right eye / left eye", "Cornea / anterior segment - right eye / left eye",
                                                             "Intraocular pressure - right eye / left eye, if measured", "Fundus - right eye / left eye, if examined; other findings"]},
        REPORTS, IMPRESSION, MANAGEMENT], "For eye drops, document the prescribed eye as well as dose, frequency and duration."),
    sheet("Dermatology", "Dermatology", [
        {"title": "C/O", "prompts": ["Rash / itching / skin lesion / hair or nail complaint and duration"]},
        {"title": "History of presenting illness", "prompts": ["Initial site, onset, spread, progression and associated symptoms", "Triggers / exposures / new medicines or products / affected contacts",
                                                                "Previous episodes / treatment and response"]},
        {"title": "Relevant history", "prompts": ["Atopy / medical conditions / medicines / family or occupational history"]},
        {"title": "O/E", "prompts": ["General condition", "Cutaneous examination - site and distribution", "Lesion morphology / number / size / colour / borders / surface",
                                     "Extent of involvement", "Hair / nails / mucosa if examined; relevant systemic findings"]},
        REPORTS, IMPRESSION, MANAGEMENT], "For topical treatment, document preparation, application site, frequency and duration."),
    sheet("Psychiatry", "Psychiatry", [
        {"title": "C/O", "prompts": ["Patient concerns and duration / informant concerns and source"]},
        {"title": "History of presenting illness", "prompts": ["Onset, course, precipitating factors and relevant psychiatric symptoms", "Sleep / appetite / energy / daily functioning / treatment response and adherence"]},
        {"title": "Relevant history", "prompts": ["Previous episodes or admissions / medical conditions / medicines", "Substance use / relevant personal, family and social history"]},
        {"title": "O/E and mental status examination", "prompts": ["Appearance / behaviour / speech", "Reported mood / observed affect", "Thought form and content / perception", "Cognition / insight / judgement"]},
        {"title": "Risk assessment if conducted", "prompts": ["Self-harm / suicide / harm to others / vulnerability", "Supporting findings / protective factors; relevant physical findings"]},
        REPORTS,
        {"title": "Provisional diagnosis and formulation", "prompts": ["Impression / relevant differentials / severity or complications"]},
        {"title": "Management", "prompts": ["Investigations / medication", "Psychological intervention / counselling", "Safety plan / family or caregiver advice",
                                            "Review / referral / admission / urgent help instructions"]}]),
    sheet("Emergency Medicine", "Emergency Medicine", [
        {"title": "Arrival and history source", "prompts": ["Arrival / assessment times / mode of arrival / history source and limitations"]},
        {"title": "C/O", "prompts": ["Complaint and duration / exact onset or last known well if relevant"]},
        {"title": "Focused history", "prompts": ["Events / associated symptoms / relevant negatives / prehospital treatment and response", "Relevant medical or surgical history / current medicines / allergies"]},
        {"title": "O/E", "prompts": ["General condition / consciousness level", "Airway / breathing / circulation", "Disability / exposure / focused findings", "CVS / RS / P/A / CNS and other relevant findings"]},
        {"title": "Available bedside tests and reports", "prompts": ["Bedside glucose / ECG / laboratory or imaging results with times"]},
        {"title": "Working diagnosis and differentials", "prompts": ["Impression / relevant differentials / severity or complications"]},
        {"title": "Management", "prompts": ["Immediate treatment / procedures and times", "Investigations requested", "Reassessment / repeat vitals / response to treatment",
                                            "Specialist consultation / disposition - discharge, observation, admission or transfer", "Discharge treatment, advice and follow-up / urgent return instructions"]}]),
    sheet("Urology", "Urology", [
        {"title": "C/O", "prompts": ["Complaint and duration"]},
        {"title": "History of presenting illness", "prompts": ["Urinary symptoms and progression / pain site, side and radiation", "Haematuria / fever / retention / incontinence if discussed",
                                                                "Relevant sexual or reproductive symptoms / treatment tried"]},
        {"title": "Relevant history", "prompts": ["Stones / urinary infections / urological surgery / instrumentation / catheter history", "Medical conditions and current medicines"]},
        {"title": "O/E", "prompts": ["General condition", "P/A - abdominal and suprapubic findings", "Renal angle tenderness", "External genital / digital rectal examination only if performed", "Relevant systemic findings"]},
        REPORTS, IMPRESSION, MANAGEMENT], "Include fluid advice and catheter care when relevant."),
]
