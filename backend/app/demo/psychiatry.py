"""Psychiatry demo clinic: fills an EMPTY database with a realistic psychiatry OPD, made only of invented people.

    python scripts/seed_demo.py            (from the repo folder; uses the same database settings as the app)

Everything goes through the app's own API (so it is stored exactly as real use would store it); earlier visits are then
moved back in time. Logins (password demo1234):
    arun@demo.in     Dr. Arun Menon, psychiatrist on his own, visits three clinics (solo mode)
    anitha@demo.in   Dr. Anitha Varma, psychiatrist, owner and admin (sees everything)
    joseph@demo.in   Dr. Joseph Mathew, psychiatrist
    divya@demo.in    Divya Raj, front desk (Operations, Patients)
    sneha@demo.in    Sneha Thomas, psychiatric social worker (Patients)
"""
import json
from datetime import date, timedelta

from fastapi.testclient import TestClient

PASSWORD = "demo1234"
FEE = 500

# ---------------------------------------------------------------- people
PATIENTS = {
    "rahul": {"name": "Rahul Menon", "dob": "1992-03-14", "sex": "M", "phone": "9847011201", "address": "Nadakkavu, Kozhikode"},
    "fathima": {"name": "Fathima Rasheed", "dob": "1999-07-02", "sex": "F", "phone": "9847011202", "address": "Feroke, Kozhikode"},
    "suresh": {"name": "Suresh Nair", "dob": "1981-11-23", "sex": "M", "phone": "9847011203", "address": "Kallai, Kozhikode"},
    "ancy": {"name": "Ancy Thomas", "dob": "2004-01-30", "sex": "F", "phone": "9847011204", "address": "Medical College, Kozhikode"},
    "vishnu": {"name": "Vishnu Prasad", "dob": "1988-05-09", "sex": "M", "phone": "9847011205", "address": "Ramanattukara"},
    "lakshmi": {"name": "Lakshmi Devi", "dob": "1965-09-17", "sex": "F", "phone": "9847011206", "address": "Kunnamangalam"},
    "arjun": {"name": "Arjun Krishnan", "dob": "2007-02-11", "sex": "M", "phone": "9847011207", "address": "West Hill, Kozhikode"},
    "meenakshi": {"name": "Meenakshi Iyer", "dob": "1997-12-05", "sex": "F", "phone": "9847011208", "address": "Eranhipalam, Kozhikode"},
    "nikhil": {"name": "Nikhil Joseph", "dob": "2010-06-21", "sex": "M", "phone": "9847011209", "address": "Mavoor Road, Kozhikode"},
    "haris": {"name": "Haris K", "dob": "1995-08-28", "sex": "M", "phone": "9847011210", "address": "Beypore"},
}

# ---------------------------------------------------------------- past visits, each with its signed note
# said: what was dictated, sentence by sentence (T1, T2...). sections: psychiatry case-sheet section -> (text, cited sentences).
# Sections: 1 C/O, 2 History of presenting illness, 3 Relevant history, 4 O/E and mental status examination,
# 5 Risk assessment if conducted, 6 Available reports, 7 Provisional diagnosis and formulation, 8 Management.
HISTORY = [
    # Rahul: moderate depressive episode, improving on escitalopram
    ("rahul", 84, "anitha", [
        "Low mood and loss of interest for two months, brought by wife.",
        "Sleeps about four hours, wakes at 3 am, appetite reduced, lost about 4 kg.",
        "Stopped going to the gym and avoids friends, struggling at work.",
        "No previous psychiatric illness, no substance use apart from occasional alcohol.",
        "Looks sad, psychomotor slowing, speech low in volume, mood low, affect constricted, no psychotic features, insight present.",
        "Passive death wishes in the last week, no plan or intent, protective factors are his daughter and wife.",
        "PHQ-9 score is 19.",
        "This is a moderate depressive episode without psychotic symptoms.",
        "Start escitalopram 10 mg once daily after breakfast for 4 weeks.",
        "Safety plan discussed with wife, review in 4 weeks or earlier if thoughts of self-harm."],
     {"1": ("Low mood and loss of interest for 2 months; brought by wife.", [1]),
      "2": ("Early-morning waking (sleeps ~4 h), reduced appetite with ~4 kg weight loss, social withdrawal, stopped exercise, struggling at work.", [2, 3]),
      "3": ("No past psychiatric illness. Occasional alcohol, no other substance use.", [4]),
      "4": ("Sad, psychomotor slowing, low-volume speech. Mood low, affect constricted. No psychotic features. Insight present. PHQ-9 19.", [5, 7]),
      "5": ("Passive death wishes in the past week; no plan or intent. Protective factors: daughter, wife.", [6]),
      "7": ("Moderate depressive episode without psychotic symptoms.", [8]),
      "8": ("Escitalopram 10 mg once daily. Safety plan with wife. Review in 4 weeks, earlier if thoughts of self-harm.", [9, 10])},
     {"Weight": "68"}, [("Escitalopram 10 mg", "0-0-1", "28 days", "after breakfast")], None, None),
    ("rahul", 56, "anitha", [
        "Review after four weeks of escitalopram.",
        "Mood slightly better, sleeping five to six hours, appetite improving.",
        "Mild nausea in the first week, now settled.",
        "Mood low but reactive, affect less constricted, no psychotic features.",
        "No death wishes now.",
        "PHQ-9 score is 14.",
        "Partial response to escitalopram, depressive episode improving.",
        "Increase escitalopram to 15 mg once daily for 4 weeks, review in 4 weeks."],
     {"1": ("Review after 4 weeks of escitalopram.", [1]),
      "2": ("Mood slightly better, sleeping 5-6 h, appetite improving. Mild nausea in week 1, now settled.", [2, 3]),
      "4": ("Mood low but reactive, affect less constricted. No psychotic features. PHQ-9 14.", [4, 6]),
      "5": ("No death wishes.", [5]),
      "7": ("Moderate depressive episode, partial response.", [7]),
      "8": ("Increase escitalopram to 15 mg once daily. Review in 4 weeks.", [8])},
     {"Weight": "69"}, [("Escitalopram 15 mg", "0-0-1", "28 days", "after breakfast")], None, None),
    ("rahul", 28, "anitha", [
        "Feels much better, back at the gym and enjoying work again.",
        "Sleep seven hours, appetite normal, weight up by 2 kg.",
        "Euthymic, reactive affect, no death wishes.",
        "PHQ-9 score is 9.",
        "Depressive episode in partial remission.",
        "Continue escitalopram 15 mg once daily for 8 weeks, continue for at least 6 to 9 months after recovery."],
     {"1": ("Follow-up: feels much better, back at the gym, enjoying work.", [1]),
      "2": ("Sleep 7 h, appetite normal, weight up 2 kg.", [2]),
      "4": ("Euthymic, reactive affect. PHQ-9 9.", [3, 4]),
      "5": ("No death wishes.", [3]),
      "7": ("Moderate depressive episode, in partial remission.", [5]),
      "8": ("Continue escitalopram 15 mg once daily; continue 6-9 months after recovery. Review in 8 weeks.", [6])},
     {"Weight": "70"}, [("Escitalopram 15 mg", "0-0-1", "56 days", "after breakfast")], None, None),

    # Fathima: generalised anxiety with panic attacks
    ("fathima", 70, "anitha", [
        "Constant worry about family and exams for eight months.",
        "Two episodes of sudden palpitations, breathlessness and fear of dying in the last month, each lasting fifteen minutes.",
        "Restless, tired, poor concentration, muscle tension, difficulty falling asleep.",
        "No medical illness, thyroid tests from her GP were normal.",
        "Anxious, fidgety, mood anxious, no depressive cognitions, no psychotic features, good insight.",
        "No suicidal thoughts.",
        "This is generalised anxiety disorder with panic attacks.",
        "Start sertraline 25 mg once daily for one week then 50 mg once daily, propranolol 10 mg as needed for palpitations up to twice a day.",
        "Psychoeducation and breathing exercises taught, referred for CBT, review in four weeks."],
     {"1": ("Excessive worry about family and exams for 8 months; two panic attacks in the last month.", [1, 2]),
      "2": ("Panic attacks: sudden palpitations, breathlessness, fear of dying, ~15 min each. Restlessness, fatigue, poor concentration, muscle tension, initial insomnia.", [2, 3]),
      "3": ("No medical illness.", [4]),
      "4": ("Anxious, fidgety. Mood anxious. No depressive cognitions or psychotic features. Good insight.", [5]),
      "5": ("No suicidal thoughts.", [6]),
      "6": ("Thyroid function normal (from GP).", [4]),
      "7": ("Generalised anxiety disorder with panic attacks.", [7]),
      "8": ("Sertraline 25 mg once daily for 1 week, then 50 mg. Propranolol 10 mg as needed (max twice daily). Psychoeducation, breathing exercises; referred for CBT. Review in 4 weeks.", [8, 9])},
     {"BP": "118/76", "Pulse": "96"}, [("Sertraline 50 mg", "0-0-1", "28 days", "25 mg (half tablet) for the first week"),
                                       ("Propranolol 10 mg", "as needed", "28 days", "for palpitations, max twice a day")], None, None),
    ("fathima", 42, "anitha", [
        "Fewer worries, one mild panic attack in four weeks.",
        "Started CBT, has had three sessions.",
        "Used propranolol twice only.",
        "Less anxious, settled, good rapport.",
        "Generalised anxiety disorder improving.",
        "Continue sertraline 50 mg once daily for 4 weeks and continue CBT, review in 4 weeks."],
     {"1": ("Review: fewer worries, one mild panic attack in 4 weeks.", [1]),
      "2": ("3 CBT sessions done. Propranolol used twice.", [2, 3]),
      "4": ("Less anxious, settled, good rapport.", [4]),
      "7": ("Generalised anxiety disorder, improving.", [5]),
      "8": ("Continue sertraline 50 mg once daily and CBT. Review in 4 weeks.", [6])},
     {"Pulse": "84"}, [("Sertraline 50 mg", "0-0-1", "28 days", "")], None, None),
    ("fathima", 14, "anitha", [
        "No panic attacks in the last month, sleeping well.",
        "Still worries before exams but copes using CBT skills.",
        "Calm, euthymic, good insight.",
        "Generalised anxiety disorder in remission.",
        "Continue sertraline 50 mg once daily for 8 weeks, review in 2 weeks after exams."],
     {"1": ("Follow-up: no panic attacks in a month, sleeping well.", [1]),
      "2": ("Some exam worry; copes with CBT skills.", [2]),
      "4": ("Calm, euthymic, good insight.", [3]),
      "7": ("Generalised anxiety disorder, in remission.", [4]),
      "8": ("Continue sertraline 50 mg once daily. Review in 2 weeks, after exams.", [5])},
     {"Pulse": "78"}, [("Sertraline 50 mg", "0-0-1", "56 days", "")], None, None),

    # Suresh: bipolar I disorder on lithium (one note later corrected by an addendum)
    ("suresh", 90, "anitha", [
        "Known bipolar disorder for ten years, two past manic episodes needing admission, last one in 2021.",
        "Stable on lithium, mood fine, sleeping well, working as a bank clerk.",
        "Mild hand tremor, no diarrhoea or vomiting.",
        "Euthymic, fine tremor of both hands, no psychotic features, insight present.",
        "Bipolar affective disorder, currently in remission.",
        "Continue lithium 800 mg at night for 30 days, lithium level, kidney and thyroid tests before next visit."],
     {"1": ("Routine review; bipolar disorder for 10 years.", [1]),
      "2": ("Stable on lithium, mood normal, sleeping well, working. Mild hand tremor; no GI side effects.", [2, 3]),
      "3": ("Two past manic episodes needing admission, last in 2021.", [1]),
      "4": ("Euthymic. Fine tremor of both hands. No psychotic features. Insight present.", [4]),
      "7": ("Bipolar affective disorder, currently in remission.", [5]),
      "8": ("Continue lithium 800 mg at night. Lithium level, renal and thyroid function before next visit.", [6])},
     {"BP": "128/82", "Weight": "74"}, [("Lithium carbonate 400 mg", "0-0-2", "30 days", "at night, drink plenty of water")], None, None),
    ("suresh", 60, "anitha", [
        "Brought the blood reports.",
        "Lithium level is 0.6 mmol/L, creatinine 0.9, TSH 3.1.",
        "Mood stable, sleep normal, no side effects apart from mild tremor.",
        "Euthymic, no psychotic features.",
        "Bipolar affective disorder in remission, lithium level in range.",
        "Continue lithium 800 mg at night for 30 days, repeat lithium level in three months."],
     {"1": ("Review with blood reports.", [1]),
      "2": ("Mood stable, sleep normal; mild tremor only.", [3]),
      "4": ("Euthymic. No psychotic features.", [4]),
      "6": ("Lithium 0.6 mmol/L, creatinine 0.9 mg/dL, TSH 3.1.", [2]),
      "7": ("Bipolar affective disorder in remission; lithium level in range.", [5]),
      "8": ("Continue lithium 800 mg at night. Repeat lithium level in 3 months.", [6])},
     {"BP": "126/80"}, [("Lithium carbonate 400 mg", "0-0-2", "30 days", "at night, drink plenty of water")],
     ("suresh_labs", "lithium_kft_tft.txt", "Lithium, kidney and thyroid panel. Serum lithium 0.8 mmol/L (12 h post dose). Creatinine 0.9 mg/dL. Urea 24 mg/dL. TSH 3.1 mIU/L. Sodium 139 mmol/L."),
     "Correction: the lithium level in the report is 0.8 mmol/L, not 0.6. Still within the maintenance range; plan unchanged."),
    ("suresh", 30, "anitha", [
        "Mood stable, slept less for two nights after a family function but settled.",
        "No increased talk or spending.",
        "Euthymic, no pressure of speech, no psychotic features.",
        "Bipolar affective disorder in remission.",
        "Continue lithium 800 mg at night for 30 days, sleep hygiene discussed, review in 4 weeks."],
     {"1": ("Follow-up: mood stable.", [1]),
      "2": ("Two nights of less sleep after a family function, settled. No increased talk or spending.", [1, 2]),
      "4": ("Euthymic. No pressure of speech. No psychotic features.", [3]),
      "7": ("Bipolar affective disorder in remission.", [4]),
      "8": ("Continue lithium 800 mg at night. Sleep hygiene. Review in 4 weeks.", [5])},
     {"BP": "124/80", "Weight": "75"}, [("Lithium carbonate 400 mg", "0-0-2", "30 days", "at night, drink plenty of water")], None, None),

    # Ancy: obsessive-compulsive disorder
    ("ancy", 63, "anitha", [
        "Repeated hand washing for two to three hours a day and fear of contamination for one year.",
        "Checks the door lock many times before leaving, late for college daily.",
        "Knows the thoughts are excessive but cannot stop them.",
        "Anxious, obsessions of contamination, washing and checking compulsions, insight good.",
        "No suicidal thoughts.",
        "Y-BOCS score is 28.",
        "This is obsessive-compulsive disorder with good insight.",
        "Start fluoxetine 20 mg once daily after breakfast for 4 weeks, referred for exposure and response prevention therapy."],
     {"1": ("Excessive hand washing (2-3 h/day) and contamination fear for 1 year.", [1]),
      "2": ("Repeated checking of door locks; late for college daily. Recognises thoughts as excessive.", [2, 3]),
      "4": ("Anxious. Contamination obsessions; washing and checking compulsions. Good insight. Y-BOCS 28.", [4, 6]),
      "5": ("No suicidal thoughts.", [5]),
      "7": ("Obsessive-compulsive disorder, good insight.", [7]),
      "8": ("Fluoxetine 20 mg once daily. Referred for exposure and response prevention (ERP). Review in 4 weeks.", [8])},
     {}, [("Fluoxetine 20 mg", "1-0-0", "28 days", "after breakfast")], None, None),
    ("ancy", 35, "anitha", [
        "Washing reduced to about one hour a day, started ERP sessions.",
        "Y-BOCS score is 21.",
        "Less anxious, insight good.",
        "Obsessive-compulsive disorder, partial response.",
        "Increase fluoxetine to 40 mg once daily after breakfast for 4 weeks, continue ERP."],
     {"1": ("Review: washing down to ~1 h/day; ERP started.", [1]),
      "4": ("Less anxious, good insight. Y-BOCS 21.", [2, 3]),
      "7": ("Obsessive-compulsive disorder, partial response.", [4]),
      "8": ("Increase fluoxetine to 40 mg once daily. Continue ERP. Review in 4 weeks.", [5])},
     {}, [("Fluoxetine 20 mg", "2-0-0", "28 days", "after breakfast")], None, None),

    # Vishnu: alcohol dependence syndrome
    ("vishnu", 49, "anitha", [
        "Drinking about 180 ml of brandy daily for six years, morning drinking for one year.",
        "Tremors and sweating in the morning if he does not drink, wants to stop.",
        "Wife reports anger outbursts when drunk, missed work often.",
        "Last drink yesterday night.",
        "Mild tremor, sweating, oriented, mood irritable, no hallucinations.",
        "No suicidal thoughts, no thoughts of harming others.",
        "Alcohol dependence syndrome with mild withdrawal.",
        "Start chlordiazepoxide 10 mg three times a day for 5 days then taper, thiamine 100 mg twice daily for 30 days, liver function tests, motivational counselling with wife."],
     {"1": ("Wants to stop drinking. ~180 ml brandy daily for 6 years; morning drinking for 1 year.", [1, 2]),
      "2": ("Morning tremor and sweating without alcohol. Anger outbursts when drunk; frequent missed work (wife). Last drink last night.", [2, 3, 4]),
      "4": ("Mild tremor, sweating. Oriented. Mood irritable. No hallucinations.", [5]),
      "5": ("No suicidal or homicidal thoughts.", [6]),
      "7": ("Alcohol dependence syndrome with mild withdrawal.", [7]),
      "8": ("Chlordiazepoxide 10 mg three times daily for 5 days, then taper. Thiamine 100 mg twice daily. LFT. Motivational counselling with wife.", [8])},
     {"BP": "142/90", "Pulse": "102"}, [("Chlordiazepoxide 10 mg", "1-1-1", "5 days", "then taper as advised"),
                                        ("Thiamine 100 mg", "1-0-1", "30 days", "")], None, None),
    ("vishnu", 21, "anitha", [
        "Abstinent for four weeks, attending AA meetings twice a week.",
        "Brought the liver function report, GGT is 96 and SGPT 58.",
        "Cravings in the evening, sleep improving.",
        "Calm, euthymic, no tremor.",
        "Alcohol dependence syndrome, early remission.",
        "Start naltrexone 50 mg once daily for 30 days, continue thiamine 100 mg twice daily, repeat liver tests in two months."],
     {"1": ("Review: abstinent 4 weeks; attending AA twice weekly.", [1]),
      "2": ("Evening cravings; sleep improving.", [3]),
      "4": ("Calm, euthymic, no tremor.", [4]),
      "6": ("LFT: GGT 96 U/L, SGPT 58 U/L.", [2]),
      "7": ("Alcohol dependence syndrome, early remission.", [5]),
      "8": ("Naltrexone 50 mg once daily. Continue thiamine 100 mg twice daily. Repeat LFT in 2 months.", [6])},
     {"BP": "128/84", "Pulse": "80"}, [("Naltrexone 50 mg", "1-0-0", "30 days", "after breakfast"), ("Thiamine 100 mg", "1-0-1", "30 days", "")],
     ("vishnu_lft", "lft.txt", "Liver function test. SGPT 58 U/L. SGOT 44 U/L. GGT 96 U/L. Total bilirubin 0.9 mg/dL. Albumin 4.1 g/dL."), None),

    # Lakshmi: late-life depression with insomnia (Dr Joseph)
    ("lakshmi", 40, "joseph", [
        "Poor sleep and sadness since her husband died six months ago.",
        "Lies awake till 2 am, lost interest in temple visits, eats less.",
        "Known hypertension on amlodipine, no memory complaints.",
        "Sad, tearful, psychomotor normal, mood low, no psychotic features, cognition intact.",
        "No suicidal thoughts.",
        "This is a depressive episode, moderate, with insomnia, following bereavement.",
        "Start mirtazapine 7.5 mg at night for 4 weeks, thyroid test, grief counselling."],
     {"1": ("Poor sleep and sadness since husband's death 6 months ago.", [1]),
      "2": ("Initial insomnia (awake till 2 am), loss of interest, reduced intake.", [2]),
      "3": ("Hypertension on amlodipine. No memory complaints.", [3]),
      "4": ("Sad, tearful. Mood low. No psychotic features. Cognition intact.", [4]),
      "5": ("No suicidal thoughts.", [5]),
      "7": ("Moderate depressive episode with insomnia, following bereavement.", [6]),
      "8": ("Mirtazapine 7.5 mg at night. Thyroid function. Grief counselling. Review in 4 weeks.", [7])},
     {"BP": "146/88", "Weight": "58"}, [("Mirtazapine 7.5 mg", "0-0-1", "28 days", "at bedtime")], None, None),
    ("lakshmi", 12, "joseph", [
        "Sleeping better, about six hours.",
        "Thyroid report is normal, TSH is 2.4.",
        "Still sad in the evenings, started going to the temple again.",
        "Mood mildly low, reactive affect.",
        "Depressive episode, improving.",
        "Increase mirtazapine to 15 mg at night for 4 weeks, continue counselling."],
     {"1": ("Review: sleeping ~6 h.", [1]),
      "2": ("Evening sadness persists; resumed temple visits.", [3]),
      "4": ("Mood mildly low, reactive affect.", [4]),
      "6": ("TSH 2.4 mIU/L (normal).", [2]),
      "7": ("Moderate depressive episode, improving.", [5]),
      "8": ("Increase mirtazapine to 15 mg at night. Continue counselling. Review in 4 weeks.", [6])},
     {"BP": "138/84"}, [("Mirtazapine 15 mg", "0-0-1", "28 days", "at bedtime")],
     ("lakshmi_tft", "thyroid.txt", "Thyroid function test. TSH 2.4 mIU/L. Free T4 1.2 ng/dL."), None),

    # Arjun: first-episode schizophrenia (Dr Joseph); weight watched on olanzapine
    ("arjun", 77, "joseph", [
        "Brought by parents for hearing voices and suspiciousness for three months.",
        "Believes neighbours are plotting against him, stopped going to college, talks to himself.",
        "No substance use, no head injury.",
        "Guarded, hallucinatory behaviour, persecutory delusions, mood anxious, insight absent.",
        "No suicidal or violent thoughts at present, parents to supervise medicines.",
        "This is a first episode of schizophrenia.",
        "Start olanzapine 10 mg at night for 4 weeks, baseline weight, sugar and lipid tests, psychoeducation for family."],
     {"1": ("Hearing voices and suspiciousness for 3 months (brought by parents).", [1]),
      "2": ("Persecutory beliefs about neighbours; stopped college; talks to himself.", [2]),
      "3": ("No substance use or head injury.", [3]),
      "4": ("Guarded. Hallucinatory behaviour. Persecutory delusions. Mood anxious. Insight absent.", [4]),
      "5": ("No suicidal or violent thoughts now; parents to supervise medication.", [5]),
      "7": ("Schizophrenia, first episode.", [6]),
      "8": ("Olanzapine 10 mg at night. Baseline weight, fasting sugar, lipids. Family psychoeducation. Review in 4 weeks.", [7])},
     {"Weight": "61", "BP": "118/74"}, [("Olanzapine 10 mg", "0-0-1", "28 days", "at night")], None, None),
    ("arjun", 47, "joseph", [
        "Voices less frequent, sleeping well, still suspicious of neighbours.",
        "Weight increased to 64 kg.",
        "Less guarded, hallucinations reduced, delusions persisting, partial insight.",
        "Schizophrenia, partial response.",
        "Increase olanzapine to 15 mg at night for 4 weeks, diet and exercise advice for weight."],
     {"1": ("Review: voices less frequent, sleeping well.", [1]),
      "2": ("Still suspicious of neighbours.", [1]),
      "4": ("Less guarded. Hallucinations reduced; persecutory delusions persist. Partial insight. Weight 64 kg.", [2, 3]),
      "7": ("Schizophrenia, partial response.", [4]),
      "8": ("Increase olanzapine to 15 mg at night. Diet and exercise for weight gain. Review in 4 weeks.", [5])},
     {"Weight": "64"}, [("Olanzapine 15 mg", "0-0-1", "28 days", "at night")], None, None),
    ("arjun", 17, "joseph", [
        "No voices for two weeks, went back to college part time.",
        "Weight is 66 kg, fasting sugar 98.",
        "Calm, no hallucinatory behaviour, delusions fading, insight improving.",
        "Schizophrenia, responding to treatment.",
        "Continue olanzapine 15 mg at night for 4 weeks, weight and sugar monitoring, review in 4 weeks."],
     {"1": ("Follow-up: no voices for 2 weeks; back at college part-time.", [1]),
      "4": ("Calm. No hallucinatory behaviour. Delusions fading. Insight improving.", [3]),
      "6": ("Weight 66 kg; fasting blood sugar 98 mg/dL.", [2]),
      "7": ("Schizophrenia, responding to treatment.", [4]),
      "8": ("Continue olanzapine 15 mg at night. Monitor weight and sugar. Review in 4 weeks.", [5])},
     {"Weight": "66"}, [("Olanzapine 15 mg", "0-0-1", "28 days", "at night")], None, None),

    # Meenakshi: adult ADHD (Dr Joseph)
    ("meenakshi", 33, "joseph", [
        "Difficulty concentrating at work, misses deadlines and loses things since school days.",
        "Restless in meetings, interrupts others, school reports mention the same problems.",
        "No mood episodes, no substance use.",
        "Restless, distractible, mood euthymic, no psychotic features.",
        "Adult attention deficit hyperactivity disorder, combined type.",
        "Start atomoxetine 40 mg once daily after breakfast for 4 weeks, organisational strategies discussed."],
     {"1": ("Poor concentration, missed deadlines, losing things since school.", [1]),
      "2": ("Restlessness, interrupting others; school reports describe the same.", [2]),
      "3": ("No mood episodes or substance use.", [3]),
      "4": ("Restless, distractible. Euthymic. No psychotic features.", [4]),
      "7": ("Adult ADHD, combined type.", [5]),
      "8": ("Atomoxetine 40 mg once daily. Organisational strategies. Review in 4 weeks.", [6])},
     {"BP": "112/72", "Pulse": "76"}, [("Atomoxetine 40 mg", "1-0-0", "28 days", "after breakfast")], None, None),

    # Nikhil: adolescent with adjustment disorder; counselling only, no medicine
    ("nikhil", 25, "anitha", [
        "Brought by mother, irritable and crying often since moving to a new school two months ago.",
        "Says he has no friends there, headaches on school mornings, marks dropped.",
        "Mood upset but reactive, no depressive cognitions, no psychotic features.",
        "No self-harm thoughts.",
        "Adjustment disorder with mixed anxiety and depressed mood.",
        "No medicines, counselling with the psychiatric social worker weekly, school counsellor to be involved, review in 4 weeks."],
     {"1": ("Irritability and crying since changing school 2 months ago (mother).", [1]),
      "2": ("No friends at new school; headaches on school mornings; marks dropped.", [2]),
      "4": ("Mood upset but reactive. No depressive cognitions or psychotic features.", [3]),
      "5": ("No self-harm thoughts.", [4]),
      "7": ("Adjustment disorder with mixed anxiety and depressed mood.", [5]),
      "8": ("No medication. Weekly counselling with the psychiatric social worker; involve school counsellor. Review in 4 weeks.", [6])},
     {}, [], None, None),

    # Haris: PTSD after a road accident (Dr Joseph)
    ("haris", 8, "joseph", [
        "Nightmares and flashbacks of a bike accident three months ago.",
        "Avoids riding and the road where it happened, startles at horns, sleep poor.",
        "Anxious, hypervigilant, mood low, no psychotic features.",
        "No suicidal thoughts.",
        "This is post-traumatic stress disorder.",
        "Start sertraline 50 mg once daily and prazosin 1 mg at night for nightmares for 4 weeks, trauma-focused therapy referral."],
     {"1": ("Nightmares and flashbacks after a bike accident 3 months ago.", [1]),
      "2": ("Avoids riding and the accident site; startle to horns; poor sleep.", [2]),
      "4": ("Anxious, hypervigilant. Mood low. No psychotic features.", [3]),
      "5": ("No suicidal thoughts.", [4]),
      "7": ("Post-traumatic stress disorder.", [5]),
      "8": ("Sertraline 50 mg once daily. Prazosin 1 mg at night for nightmares. Trauma-focused therapy referral. Review in 4 weeks.", [6])},
     {"BP": "124/82", "Pulse": "92"}, [("Sertraline 50 mg", "1-0-0", "28 days", "after breakfast"), ("Prazosin 1 mg", "0-0-1", "28 days", "at night; get up slowly")], None, None),
]

# what Fathima's doctor dictates in today's live consultation (the note is left as a draft to show Generate note)
TODAY_DICTATION = ("Exams are over, she is relaxed and sleeping well. No panic attacks in six weeks. "
                   "Wants to know how long to continue the tablets. Calm, euthymic, good insight. "
                   "Generalised anxiety disorder in remission. Continue sertraline 50 mg once daily for 3 months, then plan a slow taper. "
                   "Review in 6 weeks.")


def seed(client: TestClient | None = None) -> bool:
    """Builds the demo clinic. Returns False (and changes nothing) when the database already has a clinic."""
    from app.main import app
    from app.shared import db as database
    from app.shared.db import connect

    database.init()   # tables first: a brand-new database has none yet
    db = connect()
    try:
        if db.execute("select count(*) from clinics").fetchone()[0]:
            return False
    finally:
        db.close()

    with (client or TestClient(app)) as c:
        def call(method, path, tok=None, **kw):
            r = c.request(method, "/api" + path, headers={"Authorization": f"Bearer {tok}"} if tok else {}, **kw)
            if r.status_code >= 400:
                raise RuntimeError(f"{method} {path}: {r.status_code} {r.text[:200]}")
            return r.json()

        # clinic, owner and team
        owner = call("POST", "/onboarding/owner", json={"name": "Dr. Anitha Varma", "email": "anitha@demo.in", "password": PASSWORD,
                                                         "phone": "9847000101", "is_doctor": True, "speciality": "Psychiatry"})["token"]
        call("PUT", "/clinic", owner, json={"name": "Manas Mind Clinic", "phone": "0495 2720 100", "address": "Mavoor Road, Kozhikode"})
        all_day = [{"start": "00:00", "end": "23:59"}]   # while seeding, so walk-ins work at any hour; real hours are set at the end
        call("PUT", "/clinic/rules", owner, json={"fee": FEE, "days": [0, 1, 2, 3, 4, 5], "limit_by": "patients", "limit_value": 20,
                                                   "token_timing": "booking", "sessions": all_day})
        call("POST", "/onboarding/finish", owner)
        tokens, ids = {"anitha": owner}, {"anitha": call("GET", "/me", owner)["member"]["id"]}
        for key, body in [("joseph", {"kind": "doctor", "name": "Dr. Joseph Mathew", "email": "joseph@demo.in", "phone": "9847000102",
                                      "speciality": "Psychiatry", "screens": ["consultation", "patients"]}),
                          ("divya", {"kind": "staff", "name": "Divya Raj", "email": "divya@demo.in", "phone": "9847000103",
                                     "designation": "Front desk", "screens": ["operations", "patients"]}),
                          ("sneha", {"kind": "staff", "name": "Sneha Thomas", "email": "sneha@demo.in", "phone": "9847000104",
                                     "designation": "Psychiatric social worker", "screens": ["patients"]})]:
            m = call("POST", "/members", owner, json=body)
            tokens[key] = call("POST", "/invites/accept", json={"code": m["invite_code"], "password": PASSWORD})["token"]
            ids[key] = m["id"]

        patients = {k: call("POST", "/patients", tokens["divya"], json=p | {"consent": True})["id"] for k, p in PATIENTS.items()}
        today = date.today()   # the clinic's day: app/__init__.py sets the process time zone to CLINIC_TZ
        moves = []   # (visit_id, days_ago, addendum_after_days)

        def finished_visit(pkey, doctor, said, sections, vitals, rx, doc=None, method="cash"):
            v = call("POST", "/visits/walk-in", tokens["divya"], json={"patient_id": patients[pkey], "doctor_id": ids[doctor], "payment_method": method})
            if doc:
                call("POST", f"/visits/{v['id']}/documents", tokens["divya"], files={"file": (doc[1], doc[2].encode(), "text/plain")})
            call("POST", f"/visits/{v['id']}/start", tokens[doctor])
            call("PUT", f"/visits/{v['id']}/text", tokens[doctor], json={"text": " ".join(said), "rev": 0})
            n = call("POST", f"/visits/{v['id']}/note/draft", tokens[doctor])
            call("PUT", f"/notes/{n['id']}", tokens[doctor], json={
                "sections": {k: t for k, (t, _) in sections.items()}, "vitals": vitals,
                "rx": [{"medicine": m, "dose": d, "duration": du, "instructions": i} for m, d, du, i in rx]})
            # citations: each section cites the dictated sentences it came from, as the AI draft would
            db = connect()
            try:
                db.execute("update notes set citations = ?, sources = ?, edited = 0 where id = ?",
                           (json.dumps({k: [f"T{i}" for i in cites] for k, (_, cites) in sections.items()}),
                            json.dumps({f"T{i + 1}": s for i, s in enumerate(said)}), n["id"]))
                db.commit()
            finally:
                db.close()
            call("POST", f"/notes/{n['id']}/sign", tokens[doctor])
            return v, n

        for pkey, days_ago, doctor, said, sections, vitals, rx, doc, addendum in HISTORY:
            v, n = finished_visit(pkey, doctor, said, sections, vitals, rx, doc, method="upi" if days_ago % 2 else "cash")
            if addendum:
                call("POST", f"/notes/{n['id']}/addenda", tokens[doctor], json={"text": addendum})
            if pkey == "vishnu" and days_ago == 21:   # charged twice at the desk; half refunded
                call("POST", f"/visits/{v['id']}/refund", owner, json={"amount": 250, "reason": "Charged twice at the desk"})
            move_back(v["id"], n["id"], days_ago, today)

        # ---------------------------------------------------------------- today
        # Ancy: seen and signed this morning
        v, n = finished_visit("ancy", "anitha", [
            "Washing now under thirty minutes a day, back to attending college on time.",
            "Y-BOCS score is 12.",
            "Relaxed, mild residual obsessions, insight good.",
            "Obsessive-compulsive disorder, good response.",
            "Continue fluoxetine 40 mg once daily after breakfast for 8 weeks, continue ERP, review in 8 weeks."],
            {"1": ("Follow-up: washing under 30 min/day; attending college on time.", [1]),
             "4": ("Relaxed. Mild residual obsessions. Good insight. Y-BOCS 12.", [2, 3]),
             "7": ("Obsessive-compulsive disorder, good response.", [4]),
             "8": ("Continue fluoxetine 40 mg once daily and ERP. Review in 8 weeks.", [5])},
            {}, [("Fluoxetine 20 mg", "2-0-0", "56 days", "after breakfast")], method="card")
        # Fathima: in consultation now; dictation done, note drafted, not signed
        v = call("POST", "/visits/walk-in", tokens["divya"], json={"patient_id": patients["fathima"], "doctor_id": ids["anitha"], "payment_method": "upi"})
        call("POST", f"/visits/{v['id']}/start", owner)
        call("PUT", f"/visits/{v['id']}/text", owner, json={"text": TODAY_DICTATION, "rev": 0})
        n = call("POST", f"/visits/{v['id']}/note/draft", owner)
        said = [s.strip().rstrip(".") + "." for s in TODAY_DICTATION.split(". ") if s.strip()]   # as the draft would cite it
        draft = {"1": ("Review after exams: relaxed, sleeping well.", [1]), "2": ("No panic attacks in 6 weeks. Asks how long to continue medication.", [2, 3]),
                 "4": ("Calm, euthymic, good insight.", [4]), "7": ("Generalised anxiety disorder in remission.", [5]),
                 "8": ("Continue sertraline 50 mg once daily for 3 months, then plan a slow taper. Review in 6 weeks.", [6, 7])}
        call("PUT", f"/notes/{n['id']}", owner, json={"sections": {k: t for k, (t, _) in draft.items()}, "vitals": {"Pulse": "74"},
                                                       "rx": [{"medicine": "Sertraline 50 mg", "dose": "0-0-1", "duration": "90 days", "instructions": ""}]})
        db = connect()
        try:   # an untouched AI draft: cited, not marked as edited
            db.execute("update notes set citations = ?, sources = ?, edited = 0 where id = ?",
                       (json.dumps({k: [f"T{i}" for i in c] for k, (_, c) in draft.items()}), json.dumps({f"T{i + 1}": s for i, s in enumerate(said)}), n["id"]))
            db.commit()
        finally:
            db.close()
        fathima_today = v["id"]
        # waiting with their payment taken
        waiting = [call("POST", "/visits/walk-in", tokens["divya"], json={"patient_id": patients[p], "doctor_id": ids[d], "payment_method": m})["id"]
                   for p, d, m in [("rahul", "anitha", "upi"), ("vishnu", "anitha", "cash"), ("nikhil", "anitha", "cash"), ("haris", "joseph", "upi")]]
        # booked for today, not yet arrived
        for p, d in [("suresh", "anitha"), ("lakshmi", "joseph"), ("meenakshi", "joseph")]:
            call("POST", "/visits", tokens["divya"], json={"patient_id": patients[p], "doctor_id": ids[d], "date": today.isoformat()})
        # Suresh's new lithium report, uploaded at the desk before he is seen
        sv = [x for x in call("GET", f"/operations/day?date={today.isoformat()}", owner)["visits"] if x["patient_id"] == patients["suresh"]][0]
        call("POST", f"/visits/{sv['id']}/arrive", tokens["divya"], json={"payment_method": "card"})
        call("POST", f"/visits/{sv['id']}/documents", tokens["divya"], files={"file": ("lithium_level_followup.txt",
             b"Serum lithium 0.7 mmol/L (12 h post dose). Creatinine 0.9 mg/dL. TSH 3.4 mIU/L.", "text/plain")})
        day = call("GET", f"/operations/day?date={today.isoformat()}", owner)["visits"]
        meena = [x for x in day if x["patient_id"] == patients["meenakshi"]][0]
        call("POST", f"/visits/{meena['id']}/cancel", tokens["divya"], json={"reason": "Patient asked to come next week"})

        # ---------------------------------------------------------------- the coming days
        for p, d, ahead in [("meenakshi", "joseph", 6), ("rahul", "anitha", 27), ("ancy", "anitha", 55), ("arjun", "joseph", 12), ("haris", "joseph", 20)]:
            day_ = next_open(today, ahead)
            call("POST", "/visits", tokens["divya"], json={"patient_id": patients[p], "doctor_id": ids[d], "date": day_.isoformat()})
        call("POST", "/waitlist", tokens["divya"], json={"patient_id": patients["lakshmi"], "doctor_id": ids["joseph"], "date": next_open(today, 2).isoformat()})

        # ---------------------------------------------------------------- team: attendance and leave
        for who, at in (("anitha", "08:50"), ("divya", "08:45"), ("sneha", "09:02"), ("joseph", "09:10")):   # a normal morning, whatever the hour of loading
            call("PUT", f"/attendance/{ids[who]}/{today.isoformat()}", owner, json={"status": "present", "check_in": at})
        for back in range(1, 15):
            d = today - timedelta(days=back)
            if d.weekday() == 6:
                continue
            for who, status, at in [("divya", "late" if back == 3 else "present", "09:40" if back == 3 else "08:55"),
                                    ("sneha", "half" if back == 5 else "present", "09:05"), ("joseph", "present", "09:15")]:
                call("PUT", f"/attendance/{ids[who]}/{d.isoformat()}", owner, json={"status": status, "check_in": at})
        ljoseph = call("POST", "/leave", tokens["joseph"], json={"start_date": next_open(today, 15).isoformat(), "end_date": next_open(today, 17).isoformat(),
                                                                "type": "earned", "reason": "Conference: Indian Psychiatric Society, Kerala branch"})
        call("POST", f"/leave/{ljoseph['id']}/approve", owner)
        call("POST", "/leave", tokens["sneha"], json={"start_date": next_open(today, 9).isoformat(), "end_date": next_open(today, 9).isoformat(),
                                                      "type": "casual", "reason": "Family function"})

        # real clinic hours from now on: 9 to 1 and 4 to 8, Monday to Saturday
        call("PUT", "/clinic/rules", owner, json={"fee": FEE, "days": [0, 1, 2, 3, 4, 5], "limit_by": "patients", "limit_value": 20,
                                                   "token_timing": "booking", "sessions": [{"start": "09:00", "end": "13:00"}, {"start": "16:00", "end": "20:00"}]})
        db = connect()
        try:
            db.execute("update visits set session_start = '09:00' where session_start = '00:00'")
            db.commit()
        finally:
            db.close()
        try:   # Arjun is booked for this evening (skipped if the evening session is already over)
            call("POST", "/visits", tokens["divya"], json={"patient_id": patients["arjun"], "doctor_id": ids["joseph"], "date": today.isoformat(), "session": "16:00"})
        except RuntimeError:
            pass
        db = connect()
        try:
            db.execute("update visits set status = 'no_show' where patient_id = ? and date = ? and status = 'booked'", (patients["lakshmi"], today.isoformat()))
            db.commit()
        finally:
            db.close()

        # pre-visit briefs ready for the patients in the queue
        for vid in [fathima_today, sv["id"], *waiting]:
            call("POST", f"/visits/{vid}/brief", owner)
    return True


# ---------------------------------------------------------------- a solo psychiatrist who visits clinics
SOLO_EMAIL = "arun@demo.in"
SOLO_PLACES = ["Town Clinic, Kozhikode", "Hope Hospital, Feroke", "Riverside Clinic, Chengannur"]
SOLO_PATIENTS = {
    "anjali": {"name": "Anjali Varghese", "dob": "1994-04-12", "sex": "F", "phone": "9847022301"},
    "manoj": {"name": "Manoj Kumar", "dob": "1979-10-03", "sex": "M", "phone": "9847022302"},
    "reshma": {"name": "Reshma Babu", "dob": "2001-08-19", "sex": "F"},
    "george": {"name": "George Mathew", "dob": "1958-01-27", "sex": "M", "phone": "9847022304"},
}
# (patient, days ago, place index, said, sections, rx)
SOLO_HISTORY = [
    ("anjali", 56, 0, ["Feeling low for three months after moving cities, poor sleep, crying spells.", "No thoughts of self-harm.",
                       "Low mood, reactive affect, no psychotic features.", "Moderate depressive episode.",
                       "Start sertraline 50 mg once daily at night, sleep hygiene, review in four weeks."],
     {"1": ("Low mood for 3 months after moving cities; poor sleep; crying spells.", [1]), "5": ("No thoughts of self-harm.", [2]),
      "4": ("Low mood, reactive affect. No psychotic features.", [3]), "7": ("Moderate depressive episode.", [4]),
      "8": ("Start sertraline 50 mg at night. Sleep hygiene. Review in 4 weeks.", [5])},
     [("Sertraline 50 mg", "0-0-1", "28 days", "after food")]),
    ("anjali", 27, 1, ["Mood better, sleeping six hours, back at work.", "Mild nausea in the first week, settled.",
                       "Euthymic, reactive, good insight.", "Moderate depressive episode, improving.", "Continue sertraline 50 mg, review in six weeks."],
     {"1": ("Follow-up: mood better, sleeping 6 hours, back at work.", [1]), "2": ("Mild nausea in week 1, settled.", [2]),
      "4": ("Euthymic, reactive, good insight.", [3]), "7": ("Moderate depressive episode, improving.", [4]),
      "8": ("Continue sertraline 50 mg. Review in 6 weeks.", [5])},
     [("Sertraline 50 mg", "0-0-1", "42 days", "after food")]),
    ("manoj", 40, 2, ["Drinking daily for ten years, wants to stop, last drink two days ago.", "Tremor and sweating since yesterday.",
                      "Oriented, mild tremor, no hallucinations.", "Alcohol dependence syndrome, mild withdrawal.",
                      "Chlordiazepoxide taper over seven days, thiamine, review in one week with family."],
     {"1": ("Daily alcohol for 10 years; wants to stop. Last drink 2 days ago.", [1]), "2": ("Tremor and sweating since yesterday.", [2]),
      "4": ("Oriented. Mild tremor. No hallucinations.", [3]), "7": ("Alcohol dependence syndrome with mild withdrawal.", [4]),
      "8": ("Chlordiazepoxide taper over 7 days. Thiamine. Review in 1 week with family.", [5])},
     [("Chlordiazepoxide 10 mg", "1-1-1", "7 days", "taper as advised"), ("Thiamine 100 mg", "1-0-0", "30 days", "")]),
    ("manoj", 32, 2, ["Completed taper, no drinking for nine days, cravings in the evening.", "Calm, cooperative.",
                      "Alcohol dependence syndrome, early abstinence.", "Start naltrexone 50 mg once daily, join support group, review in a month."],
     {"1": ("Completed taper. Abstinent 9 days; evening cravings.", [1]), "4": ("Calm, cooperative.", [2]),
      "7": ("Alcohol dependence syndrome, early abstinence.", [3]), "8": ("Start naltrexone 50 mg daily. Support group. Review in 1 month.", [4])},
     [("Naltrexone 50 mg", "1-0-0", "30 days", "after breakfast")]),
    ("george", 14, 0, ["Forgetting names and misplacing keys for a year, says his wife.", "MMSE 24 of 30.",
                       "Alert, mild recent memory loss, mood normal.", "Mild cognitive impairment, rule out reversible causes.",
                       "Thyroid, B12 and CT brain, review with reports."],
     {"1": ("Forgetting names, misplacing keys for a year (per wife).", [1]), "6": ("MMSE 24/30.", [2]),
      "4": ("Alert. Mild recent memory loss. Mood normal.", [3]), "7": ("Mild cognitive impairment; rule out reversible causes.", [4]),
      "8": ("TSH, B12, CT brain. Review with reports.", [5])}, []),
]


def seed_solo(client: TestClient | None = None) -> bool:
    """Adds Dr. Arun Menon, a psychiatrist on his own who sees patients at three clinics. Skipped if he already exists."""
    from app.main import app
    from app.shared import db as database
    from app.shared.db import connect

    database.init()
    db = connect()
    try:
        if db.execute("select 1 from members where lower(email) = ?", (SOLO_EMAIL,)).fetchone():
            return False
    finally:
        db.close()

    with (client or TestClient(app)) as c:
        def call(method, path, tok=None, **kw):
            r = c.request(method, "/api" + path, headers={"Authorization": f"Bearer {tok}"} if tok else {}, **kw)
            if r.status_code >= 400:
                raise RuntimeError(f"{method} {path}: {r.status_code} {r.text[:200]}")
            return r.json()

        tok = call("POST", "/onboarding/solo", json={"name": "Dr. Arun Menon", "email": SOLO_EMAIL, "phone": "9847000201",
                                                    "password": PASSWORD, "speciality": "Psychiatry"})["token"]
        places = [call("POST", "/locations", tok, json={"name": n})["id"] for n in SOLO_PLACES]
        patients = {k: call("POST", "/patients", tok, json=p | {"consent": True})["id"] for k, p in SOLO_PATIENTS.items()}
        today = date.today()

        def visit(pkey, place, said, sections, rx):
            v = call("POST", "/visits/quick", tok, json={"patient_id": patients[pkey], "location_id": places[place]})
            call("PUT", f"/visits/{v['id']}/text", tok, json={"text": " ".join(said), "rev": 0})
            n = call("POST", f"/visits/{v['id']}/note/draft", tok)
            call("PUT", f"/notes/{n['id']}", tok, json={"sections": {k: t for k, (t, _) in sections.items()}, "vitals": {},
                                                         "rx": [{"medicine": m, "dose": d, "duration": du, "instructions": i} for m, d, du, i in rx]})
            db = connect()
            try:
                db.execute("update notes set citations = ?, sources = ?, edited = 0 where id = ?",
                           (json.dumps({k: [f"T{i}" for i in cites] for k, (_, cites) in sections.items()}),
                            json.dumps({f"T{i + 1}": s for i, s in enumerate(said)}), n["id"]))
                db.commit()
            finally:
                db.close()
            return v, n

        for pkey, days_ago, place, said, sections, rx in SOLO_HISTORY:
            v, n = visit(pkey, place, said, sections, rx)
            call("POST", f"/notes/{n['id']}/sign", tok)
            move_back(v["id"], n["id"], days_ago, today)
        # today: Reshma's first visit, dictated and drafted, not signed yet
        visit("reshma", 0, ["Panic attacks twice a week for two months, racing heart, fear of dying.", "No substance use.",
                            "Anxious, no low mood, insight present."],
              {"1": ("Panic attacks twice weekly for 2 months: palpitations, fear of dying.", [1]),
               "3": ("No substance use.", [2]), "4": ("Anxious. No low mood. Insight present.", [3])}, [])
    return True


def next_open(today: date, ahead: int) -> date:
    """The day `ahead` days from today, moved off Sunday (the clinic is closed)."""
    d = today + timedelta(days=ahead)
    return d + timedelta(days=1) if d.weekday() == 6 else d


def move_back(visit_id: int, note_id: int, days_ago: int, today: date) -> None:
    """Moves a finished visit (its note, addenda, documents and payments) `days_ago` days into the past, off Sundays."""
    from app.shared.db import connect

    day = today - timedelta(days=days_ago)
    if day.weekday() == 6:
        day -= timedelta(days=1)
    stamp = lambda t: t and day.isoformat() + str(t)[10:]
    db = connect()
    try:
        r = db.execute("select doctor_id, paid_at, arrived_at, started_at, completed_at, created_at from visits where id = ?", (visit_id,)).fetchone()
        v = [r[i] for i in range(6)]   # by position: works for SQLite and Postgres rows
        token = db.execute("select coalesce(max(token), 0) + 1 from visits where doctor_id = ? and date = ?", (v[0], day.isoformat())).fetchone()[0]
        db.execute("update visits set date = ?, token = ?, paid_at = ?, arrived_at = ?, started_at = ?, completed_at = ?, created_at = ? where id = ?",
                   (day.isoformat(), token, *(stamp(x) for x in v[1:]), visit_id))
        r = db.execute("select signed_at, created_at, updated_at from notes where id = ?", (note_id,)).fetchone()
        n = [r[i] for i in range(3)]
        db.execute("update notes set signed_at = ?, created_at = ?, updated_at = ? where id = ?", (*(stamp(x) for x in n), note_id))
        later = (day + timedelta(days=3)).isoformat()   # a correction is signed a few days after the visit
        for r in db.execute("select id, signed_at from note_addenda where note_id = ?", (note_id,)).fetchall():
            db.execute("update note_addenda set signed_at = ? where id = ?", (later + str(r[1])[10:], r[0]))
        for r in db.execute("select id, created_at from documents where visit_id = ?", (visit_id,)).fetchall():
            db.execute("update documents set created_at = ? where id = ?", (stamp(r[1]), r[0]))
        for r in db.execute("select id, at from payments where visit_id = ?", (visit_id,)).fetchall():
            db.execute("update payments set at = ? where id = ?", (stamp(r[1]), r[0]))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    print("Psychiatry demo loaded." if seed() else "The database already has a clinic; nothing was added. Use an empty database for the demo.")
