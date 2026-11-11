"""Common lab tests and vitals: one name each, the unit we chart them in, a usual adult range, the names Indian labs print
for them, and how to convert other units. Used by the brief's charts and flags, so "S. Creatinine", "Serum creatinine"
and "CREATININE (µmol/L)" become one line in one unit. Not a full ontology: names it doesn't know stay as printed.

Usual ranges are rough adult values, used only when the report doesn't print its own (the report's range always wins).
"""
import re

# name: (unit, low, high, aliases). low/high None = no bound on that side; (None, None) = no usual range.
TESTS = {
    # vitals (from notes)
    "BP": ("mmHg", None, None, "bp bloodpressure"),
    "BP systolic": ("mmHg", 90, 139, "sbp systolic systolicbp"),
    "BP diastolic": ("mmHg", 60, 89, "dbp diastolic diastolicbp"),
    "Pulse": ("/min", 60, 100, "pulse hr heartrate pulserate pr"),
    "Respiratory rate": ("/min", 12, 20, "rr respiratoryrate resprate respiration"),
    "SpO2": ("%", 95, 100, "spo2 oxygensaturation o2sat saturation sao2"),
    "Temperature": ("°F", 97, 99.5, "temp temperature"),
    "Weight": ("kg", None, None, "weight wt bodyweight"),
    "Height": ("cm", None, None, "height ht"),
    "BMI": ("kg/m²", 18.5, 24.9, "bmi bodymassindex"),
    # sugars
    "HbA1c": ("%", 4.0, 5.6, "hba1c glycatedhb glycatedhaemoglobin glycatedhemoglobin glycosylatedhaemoglobin glycosylatedhemoglobin a1c hbaic"),
    "Fasting sugar": ("mg/dL", 70, 99, "fbs fastingsugar fastingbloodsugar fastingglucose fastingplasmaglucose fpg glucosefasting "
                                       "bloodsugarfasting fbg plasmaglucosefasting fastingbloodglucose"),
    "Random sugar": ("mg/dL", 70, 139, "rbs randomsugar randombloodsugar randomglucose rbg glucoserandom bloodsugarrandom randombloodglucose"),
    "Post-prandial sugar": ("mg/dL", 70, 139, "ppbs ppbg postprandialsugar postprandialbloodsugar postprandialglucose glucosepp "
                                              "2hrppbs ppg plasmaglucosepp postprandialbloodglucose glucosepostprandial"),
    "Average glucose": ("mg/dL", None, None, "estimatedaverageglucose eag meanbloodglucose averageglucose meanplasmaglucose"),
    "Insulin": ("µIU/mL", 2, 25, "insulin fastinginsulin"),
    # kidney and salts
    "Creatinine": ("mg/dL", 0.6, 1.3, "creatinine serumcreatinine creat"),
    "Urea": ("mg/dL", 15, 40, "urea bloodurea serumurea"),
    "BUN": ("mg/dL", 7, 20, "bun bloodureanitrogen ureanitrogen"),
    "eGFR": ("mL/min/1.73m²", 90, None, "egfr estimatedgfr gfr egfrckdepi"),
    "Uric acid": ("mg/dL", 3.5, 7.2, "uricacid serumuricacid"),
    "Sodium": ("mmol/L", 135, 145, "sodium na serumsodium"),
    "Potassium": ("mmol/L", 3.5, 5.1, "potassium k serumpotassium"),
    "Chloride": ("mmol/L", 98, 107, "chloride cl serumchloride"),
    "Bicarbonate": ("mmol/L", 22, 29, "bicarbonate hco3 totalco2 serumbicarbonate"),
    "Calcium": ("mg/dL", 8.5, 10.5, "calcium totalcalcium ca serumcalcium"),
    "Ionised calcium": ("mmol/L", 1.12, 1.32, "ionisedcalcium ionizedcalcium ica freecalcium"),
    "Phosphorus": ("mg/dL", 2.5, 4.5, "phosphorus phosphate inorganicphosphorus serumphosphorus"),
    "Magnesium": ("mg/dL", 1.7, 2.4, "magnesium mg serummagnesium"),
    "Urine albumin/creatinine ratio": ("mg/g", None, 30, "uacr acr albumincreatinineratio urinealbumincreatinineratio urinaryacr"),
    "Microalbumin": ("mg/L", None, 20, "microalbumin urinemicroalbumin urinarymicroalbumin"),
    # liver
    "Bilirubin": ("mg/dL", 0.2, 1.2, "bilirubin totalbilirubin bilirubintotal tbil serumbilirubin"),
    "Direct bilirubin": ("mg/dL", 0, 0.3, "directbilirubin bilirubindirect conjugatedbilirubin dbil"),
    "Indirect bilirubin": ("mg/dL", 0.2, 0.9, "indirectbilirubin bilirubinindirect unconjugatedbilirubin"),
    "SGOT (AST)": ("U/L", 0, 40, "sgot ast aspartateaminotransferase astsgot sgotast aspartatetransaminase"),
    "SGPT (ALT)": ("U/L", 0, 41, "sgpt alt alanineaminotransferase altsgpt sgptalt alaninetransaminase"),
    "ALP": ("U/L", 40, 129, "alp alkalinephosphatase"),
    "GGT": ("U/L", 0, 60, "ggt ggtp gammagt gammaglutamyltransferase gammaglutamyltranspeptidase"),
    "Total protein": ("g/dL", 6.0, 8.3, "totalprotein protein proteintotal serumprotein"),
    "Albumin": ("g/dL", 3.5, 5.2, "albumin serumalbumin"),
    "Globulin": ("g/dL", 2.0, 3.5, "globulin serumglobulin"),
    "A/G ratio": ("", 1.0, 2.1, "agratio albuminglobulinratio"),
    "INR": ("", 0.8, 1.2, "inr ptinr"),
    "Prothrombin time": ("s", 11, 13.5, "pt prothrombintime"),
    "aPTT": ("s", 25, 35, "aptt ptt activatedpartialthromboplastintime"),
    # lipids
    "Total cholesterol": ("mg/dL", None, 200, "cholesterol totalcholesterol cholesteroltotal tc serumcholesterol"),
    "Triglycerides": ("mg/dL", None, 150, "triglycerides tg trigs triglyceride serumtriglycerides"),
    "HDL": ("mg/dL", 40, None, "hdl hdlcholesterol hdlc"),
    "LDL": ("mg/dL", None, 100, "ldl ldlcholesterol ldlc directldl"),
    "VLDL": ("mg/dL", 5, 40, "vldl vldlcholesterol"),
    "Non-HDL cholesterol": ("mg/dL", None, 130, "nonhdl nonhdlcholesterol"),
    "Cholesterol/HDL ratio": ("", None, 5, "tchdlratio cholesterolhdlratio totalcholesterolhdlratio chol hdlratio"),
    "LDL/HDL ratio": ("", None, 3.5, "ldlhdlratio"),
    # thyroid
    "TSH": ("µIU/mL", 0.4, 4.5, "tsh thyroidstimulatinghormone ultrasensitivetsh ustsh tsh3rdgeneration"),
    "Free T4": ("ng/dL", 0.8, 1.8, "ft4 freet4 freethyroxine"),
    "Free T3": ("pg/mL", 2.3, 4.2, "ft3 freet3 freetriiodothyronine"),
    "T4": ("µg/dL", 5, 12, "t4 totalt4 thyroxine"),
    "T3": ("ng/dL", 80, 200, "t3 totalt3 triiodothyronine"),
    "Anti-TPO": ("IU/mL", None, 35, "antitpo tpoantibody antithyroidperoxidase antitpoantibody"),
    # blood count
    "Haemoglobin": ("g/dL", 12, 17, "hb hgb haemoglobin hemoglobin"),
    "WBC": ("/µL", 4000, 11000, "wbc tlc totalleucocytecount totalleukocytecount totalwbccount wbccount totalcount leucocytes leukocytes"),
    "Platelets": ("/µL", 150000, 450000, "platelets plateletcount plt"),
    "RBC": ("million/µL", 4.0, 5.9, "rbc rbccount totalrbccount erythrocytecount erythrocytes"),
    "PCV (haematocrit)": ("%", 36, 50, "pcv hct haematocrit hematocrit packedcellvolume"),
    "MCV": ("fL", 80, 100, "mcv"),
    "MCH": ("pg", 27, 33, "mch"),
    "MCHC": ("g/dL", 32, 36, "mchc"),
    "RDW": ("%", 11.5, 14.5, "rdw rdwcv"),
    "Neutrophils": ("%", 40, 75, "neutrophils neutrophil polymorphs"),
    "Lymphocytes": ("%", 20, 45, "lymphocytes lymphocyte"),
    "Monocytes": ("%", 2, 10, "monocytes monocyte"),
    "Eosinophils": ("%", 1, 6, "eosinophils eosinophil"),
    "Basophils": ("%", 0, 1, "basophils basophil"),
    "Absolute eosinophil count": ("/µL", 40, 440, "aec absoluteeosinophilcount"),
    "ESR": ("mm/hr", 0, 20, "esr erythrocytesedimentationrate"),
    "Reticulocytes": ("%", 0.5, 2.5, "reticulocytecount retic reticulocytes"),
    # inflammation, iron, vitamins
    "CRP": ("mg/L", None, 5, "crp creactiveprotein crpquantitative"),
    "hs-CRP": ("mg/L", None, 3, "hscrp highsensitivitycrp highsensitivitycreactiveprotein"),
    "Procalcitonin": ("ng/mL", None, 0.5, "procalcitonin pct"),
    "Ferritin": ("ng/mL", 30, 400, "ferritin serumferritin"),
    "Iron": ("µg/dL", 60, 170, "iron serumiron"),
    "TIBC": ("µg/dL", 250, 450, "tibc totalironbindingcapacity"),
    "Transferrin saturation": ("%", 20, 50, "transferrinsaturation tsat"),
    "Vitamin B12": ("pg/mL", 200, 900, "vitaminb12 b12 cobalamin cyanocobalamin vitb12"),
    "Vitamin D": ("ng/mL", 30, 100, "vitamind 25ohvitamind 25hydroxyvitamind vitd totalvitamind vitamind3 25ohd vitamind25oh"),
    "Folate": ("ng/mL", 5.4, None, "folate folicacid serumfolate"),
    # heart, pancreas, muscle
    "Troponin I": ("ng/mL", None, 0.04, "troponini tropi ctni hstroponini"),
    "Troponin T": ("ng/mL", None, 0.01, "troponint tropt ctnt hstroponint"),
    "CK-MB": ("U/L", None, 25, "ckmb"),
    "CPK": ("U/L", 30, 200, "cpk ck creatinekinase"),
    "BNP": ("pg/mL", None, 100, "bnp"),
    "NT-proBNP": ("pg/mL", None, 125, "ntprobnp"),
    "D-dimer": ("ng/mL", None, 500, "ddimer"),
    "LDH": ("U/L", 140, 280, "ldh lactatedehydrogenase"),
    "Amylase": ("U/L", 28, 100, "amylase serumamylase"),
    "Lipase": ("U/L", 13, 60, "lipase serumlipase"),
    # hormones
    "Prolactin": ("ng/mL", None, None, "prolactin prl"),
    "Testosterone": ("ng/dL", None, None, "testosterone totaltestosterone"),
    "Cortisol": ("µg/dL", None, None, "cortisol serumcortisol"),
    "LH": ("mIU/mL", None, None, "lh luteinisinghormone luteinizinghormone"),
    "FSH": ("mIU/mL", None, None, "fsh folliclestimulatinghormone"),
    "Oestradiol": ("pg/mL", None, None, "estradiol oestradiol e2"),
    "Progesterone": ("ng/mL", None, None, "progesterone"),
    "Beta hCG": ("mIU/mL", None, None, "betahcg bhcg hcg serumbetahcg"),
    "PSA": ("ng/mL", None, 4, "psa totalpsa"),
    # drug levels (psychiatry, neurology, cardiology)
    "Lithium": ("mmol/L", 0.6, 1.2, "lithium seruml lithiumlevel serumlithium"),
    "Valproate": ("µg/mL", 50, 100, "valproate valproicacid sodiumvalproate divalproex valproatelevel"),
    "Carbamazepine": ("µg/mL", 4, 12, "carbamazepine cbz carbamazepinelevel"),
    "Phenytoin": ("µg/mL", 10, 20, "phenytoin phenytoinlevel"),
    "Digoxin": ("ng/mL", 0.8, 2.0, "digoxin digoxinlevel"),
}

# Other units a test is reported in, and how to turn them into ours. A number is a factor; a function converts.
_GLU = {"mmol/l": 18.016}
_CHOL = {"mmol/l": 38.67}
_COUNT = {"10^3/ul": 1000, "10^9/l": 1000, "lakh/ul": 100000}
CONVERT = {
    "Fasting sugar": _GLU, "Random sugar": _GLU, "Post-prandial sugar": _GLU, "Average glucose": _GLU,
    "HbA1c": {"mmol/mol": lambda v: v / 10.929 + 2.15},
    "Creatinine": {"umol/l": 1 / 88.4}, "Urea": {"mmol/l": 6.006}, "BUN": {"mmol/l": 2.801}, "Uric acid": {"umol/l": 1 / 59.48},
    "Calcium": {"mmol/l": 4.008}, "Phosphorus": {"mmol/l": 3.097}, "Magnesium": {"mmol/l": 2.431},
    "Bilirubin": {"umol/l": 1 / 17.1}, "Direct bilirubin": {"umol/l": 1 / 17.1}, "Indirect bilirubin": {"umol/l": 1 / 17.1},
    "Total protein": {"g/l": 0.1}, "Albumin": {"g/l": 0.1}, "Globulin": {"g/l": 0.1},
    "Total cholesterol": _CHOL, "HDL": _CHOL, "LDL": _CHOL, "VLDL": _CHOL, "Non-HDL cholesterol": _CHOL,
    "Triglycerides": {"mmol/l": 88.57},
    "Free T4": {"pmol/l": 1 / 12.87}, "Free T3": {"pmol/l": 1 / 1.536}, "T4": {"nmol/l": 1 / 12.87}, "T3": {"nmol/l": 65.1},
    "Haemoglobin": {"g/l": 0.1, "mmol/l": 1.611}, "MCHC": {"g/l": 0.1},
    "WBC": _COUNT, "Platelets": _COUNT, "Absolute eosinophil count": _COUNT, "RBC": {"10^12/l": 1},
    "CRP": {"mg/dl": 10}, "hs-CRP": {"mg/dl": 10},
    "Iron": {"umol/l": 5.585}, "TIBC": {"umol/l": 5.585},
    "Vitamin B12": {"pmol/l": 1.355}, "Vitamin D": {"nmol/l": 1 / 2.496}, "Folate": {"nmol/l": 1 / 2.266},
    "Testosterone": {"nmol/l": 28.84}, "Cortisol": {"nmol/l": 1 / 27.59},
    "Temperature": {"°c": lambda v: v * 9 / 5 + 32, "c": lambda v: v * 9 / 5 + 32},
    "Weight": {"lb": 0.4536, "lbs": 0.4536}, "Height": {"m": 100, "in": 2.54, "inch": 2.54, "inches": 2.54},
}

# Spellings of the same unit, so "mg/dl", "mg%" and "mg/dL" are one unit.
_SAME_UNIT = {"mg%": "mg/dl", "gm/dl": "g/dl", "gms/dl": "g/dl", "g%": "g/dl", "gm%": "g/dl", "meq/l": "mmol/l", "iu/l": "u/l",
              "/cumm": "/ul", "/mm3": "/ul", "cells/cumm": "/ul", "cells/ul": "/ul", "/cmm": "/ul",
              "x10^3/ul": "10^3/ul", "10³/ul": "10^3/ul", "x10³/ul": "10^3/ul", "thou/ul": "10^3/ul", "k/ul": "10^3/ul",
              "10^3/cumm": "10^3/ul", "x10^9/l": "10^9/l", "lakh/cumm": "lakh/ul", "lakhs/cumm": "lakh/ul", "lakhs/ul": "lakh/ul",
              "mill/cumm": "million/ul", "million/cumm": "million/ul", "10^6/ul": "million/ul", "x10^6/ul": "million/ul",
              "mil/ul": "million/ul", "millions/cumm": "million/ul", "x10^12/l": "10^12/l",
              "miu/l": "uiu/ml", "uiu/ml": "uiu/ml", "mu/l": "uiu/ml", "ng/ml": "ng/ml", "ug/l": "ng/ml", "mcg/l": "ng/ml",
              "mcg/dl": "ug/dl", "mcg/ml": "ug/ml", "secs": "s", "sec": "s", "seconds": "s",
              "mm/1sthr": "mm/hr", "mm/hour": "mm/hr", "mm/h": "mm/hr", "bpm": "/min", "beats/min": "/min", "breaths/min": "/min",
              "kg/m2": "kg/m²", "ml/min/1.73m2": "ml/min/1.73m²", "°f": "°f", "f": "°f", "degf": "°f", "degc": "°c", "fl": "fl", "kgs": "kg"}

_ALIAS = {}
for _name, (_u, _lo, _hi, _aka) in TESTS.items():
    for _a in [re.sub(r"[^a-z0-9]", "", _name.lower()), *_aka.split()]:
        _ALIAS.setdefault(_a, _name)
_PREFIXES = ("serum", "sr", "s", "plasma", "pl", "blood")


def unit_key(unit) -> str:
    u = str(unit or "").strip().lower().replace("μ", "u").replace("µ", "u").replace(" ", "")
    return _SAME_UNIT.get(u, u)


def canonical(name) -> str:
    """Our one name for a test ("S. Creatinine" -> "Creatinine"); unknown names come back as printed."""
    key = re.sub(r"[^a-z0-9]", "", str(name or "").lower())
    if key in _ALIAS:
        return _ALIAS[key]
    for p in _PREFIXES:   # "S. Creatinine", "Serum TSH", "Plasma glucose fasting"
        if key.startswith(p) and key[len(p):] in _ALIAS:
            return _ALIAS[key[len(p):]]
    return str(name or "").strip()


def to_unit(name: str, unit):
    """A function turning a value in `unit` into our unit for `name` (None when we can't), and our unit's label.
    No unit given: taken to be ours (how notes and most Indian reports write values)."""
    if name not in TESTS:
        return (lambda v: v), str(unit or "").strip()
    ours = TESTS[name][0]
    u = unit_key(unit)
    if not u or u == unit_key(ours):
        return (lambda v: v), ours
    how = CONVERT.get(name, {}).get(u)
    if how is None:
        return None, str(unit).strip()
    return (how if callable(how) else (lambda v, f=how: v * f)), ours


def normalise(name: str, value, unit) -> tuple[str, str, object]:
    """(value text, unit, converter) in our unit; when it can't convert, the value and unit as printed (converter None)."""
    conv, label = to_unit(name, unit)
    if conv is None:
        return str(value), label, None
    try:
        v = conv(float(str(value).replace(",", "")))
    except ValueError:
        return str(value), label, None
    text = f"{v:.2f}".rstrip("0").rstrip(".") if abs(v) < 100 else f"{v:.0f}"
    return text, label, conv


def usual(name: str, unit) -> list | None:
    """The usual adult range as [low, high] (a side None when open), only for our unit."""
    t = TESTS.get(name)
    if not t or (t[1] is None and t[2] is None) or unit_key(unit) not in ("", unit_key(t[0])):
        return None
    return [t[1], t[2]]
