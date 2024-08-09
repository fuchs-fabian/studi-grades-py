import argparse
import os
import pandas as pd # type: ignore
import pdfplumber # type: ignore
import re

# TODO: Support individual file names per arg
CSV_FILE = 'grades.csv'
PDF_FILE_PART = 'abschluss'

# TODO: Support individual ects points per arg
ECTS_REQUIRED = 210
ECTS_WITHOUT_GRADE = 34

# Language Options
LANGUAGE_OPTIONS = {
    "de": {
        "general_elective_module": "Allgemeinwissenschaftliches Wahlpflichtmodul",
        "compulsory_module": "Pflichtmodule",
        "specific_elective_module": "Fachspezifisches Wahlpflichtmodul",
        "internship_semester": "Modul Praxissemester",
        "passed": "bestanden",
        "in_progress": "wip",
        "required": "Erforderlich",
        "without_grade": "Ohne Note",
        "with_grade": "Mit Note",
        "open": "Offen",
        "overall_average": "Gesamtdurchschnitt",
        "grades": "Noten",
        "exam_number": "Prüfungsnr",
        "description": "Bezeichnung der Leistung",
        "semester": "Semester",
        "attempt": "Versuch",
        "grade": "Note",
        "status": "Status",
        "ects": "ECTS",
        "remark": "Vermerk",
        "type": "Art",
        "winter_term": "Winter",
        "summer_term": "Sommer",
        "not_included_entries": "Folgende Einträge fließen nicht in die Berechnungen ein",
        "still_required_ects_without_grade": "Noch benötigte ECTS in Modulen ohne Note",
        "short_description": "Beschreibung",
        "number_of": "Anzahl",
        "average": "Durchschnitt"
    },
    "en": {
        "general_elective_module": "General Compulsory Elective Module",
        "compulsory_module": "Compulsory Subjects",
        "specific_elective_module": "Specific Compulsory Elective Module",
        "internship_semester": "Internship Semester",
        "passed": "passed",
        "in_progress": "wip",
        "required": "Required",
        "without_grade": "Without Grade",
        "with_grade": "With Grade",
        "open": "Open",
        "overall_average": "Overall Average",
        "grades": "Grades",
        "exam_number": "Code",
        "description": "Course/Module Title",
        "semester": "Semester",
        "attempt": "Attempt",
        "grade": "Local Grade",
        "status": "Result",
        "ects": "ECTS",
        "remark": "Remark",
        "type": "Type",
        "winter_term": "Winter",
        "summer_term": "Summer",
        "not_included_entries": "The following entries are not included in the calculations",
        "still_required_ects_without_grade": "ECTS still required in modules without a grade",
        "short_description": "Description",
        "number_of": "Number of",
        "average": "Average"
    }
}

# Find the PDF file
def find_pdf_file():
    for file_name in os.listdir('.'):
        if file_name.startswith(PDF_FILE_PART) and file_name.endswith('.pdf'):
            return file_name
    print(f"No suitable PDF file found. Please name the PDF file accordingly: {PDF_FILE_PART}*.pdf")
    exit()

# Extract the text from the PDF file
def extract_text_from_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text()
    return text

# Parsing the text from the PDF file into a DataFrame
# TODO: Support PDF files without attempt
def parse_pdf_text_to_df(text, language):
    lines = text.split('\n')
    data = []

    module_pattern = re.compile(r'^\d{4,}$')
    entry_pattern = re.compile(r'(\d{7})\s+(.+?)\s+(WiSe\d{2}/\d{2}|SoSe\d{2}|Winter\d{2}/\d{2}|Summer\d{2})\s+(\d+)\s+([\d.,]*)\s*(\w*)\s+(\d+)\s*(.*)?')

    kind = None

    for line in lines:
        if LANGUAGE_OPTIONS[language]['general_elective_module'] in line:
            kind = 'AWPF' # TODO: Support english version
            continue
        elif LANGUAGE_OPTIONS[language]['compulsory_module'] in line:
            kind = ''
            continue
        elif LANGUAGE_OPTIONS[language]['specific_elective_module'] in line:
            kind = 'FWPF' # TODO: Support english version
            continue
        elif LANGUAGE_OPTIONS[language]['internship_semester'] in line:
            kind = 'PS'   # TODO: Support english version
            continue

        if module_pattern.match(line):
            continue

        match = entry_pattern.match(line)
        if match:
            exam_nr, description, semester, trial, grade, status, ects, remark = match.groups()
            data.append({
                LANGUAGE_OPTIONS[language]['exam_number']: exam_nr,
                LANGUAGE_OPTIONS[language]['description']: description,
                LANGUAGE_OPTIONS[language]['semester']: semester,
                LANGUAGE_OPTIONS[language]['attempt']: trial,
                LANGUAGE_OPTIONS[language]['grade']: grade.replace(',', '.') if grade else None,
                LANGUAGE_OPTIONS[language]['status']: status,
                LANGUAGE_OPTIONS[language]['ects']: ects,
                LANGUAGE_OPTIONS[language]['remark']: remark,
                LANGUAGE_OPTIONS[language]['type']: kind
            })

    df = pd.DataFrame(data)

    df[LANGUAGE_OPTIONS[language]['grade']] = pd.to_numeric(df[LANGUAGE_OPTIONS[language]['grade']], errors='coerce')
    df[LANGUAGE_OPTIONS[language]['ects']] = pd.to_numeric(df[LANGUAGE_OPTIONS[language]['ects']], errors='coerce', downcast='integer')

    return df

# Output of a DataFrame
def print_df(df_temp, indent=True):
    if indent:
        print()
    print(df_temp.to_string(index=False))

# Sorting function for semesters
def semester_sort_key(semester):
    offset = 2000
    if any(semester.startswith(term) for term in ["WiSe", LANGUAGE_OPTIONS["en"]["winter_term"]]):
        year = offset + int(semester.split('/')[1]) if '/' in semester else offset + int(semester[-2:])
        return (year, 0)
    elif any(semester.startswith(term) for term in ["SoSe", LANGUAGE_OPTIONS["en"]["summer_term"]]):
        year = offset + int(semester[-2:])
        return (year, 1)
    else:
        return (float('inf'), 2)

# Sorting function for type
# TODO: art is not the right term for it
# TODO: Support english version
def art_sort_key(art):
    if art == 'AWPF':
        return 0
    elif art == 'FWPF':
        return 2
    else:
        return 1

# Function for sorting the DataFrame
def sort_df(df_temp, sort_art=False, language='de'):
    sort_columns = []
    ascending_flags = []

    if sort_art and LANGUAGE_OPTIONS[language]['type'] in df_temp.columns:
        df_temp['ArtSortKey'] = df_temp[LANGUAGE_OPTIONS[language]['type']].apply(art_sort_key)
        sort_columns.append('ArtSortKey')
        ascending_flags.append(True)
    
    if LANGUAGE_OPTIONS[language]['semester'] in df_temp.columns:
        df_temp['SortKey'] = df_temp[LANGUAGE_OPTIONS[language]['semester']].apply(semester_sort_key)
        sort_columns.append('SortKey')
        ascending_flags.append(True)

    if LANGUAGE_OPTIONS[language]['exam_number'] in df_temp.columns:
        sort_columns.append(LANGUAGE_OPTIONS[language]['exam_number'])
        ascending_flags.append(True)

    return df_temp.sort_values(by=sort_columns, ascending=ascending_flags).drop(columns=['SortKey']).reset_index(drop=True)

def get_df_from_csv():
    return pd.read_csv(CSV_FILE)

def get_df_from_pdf(language):
    df = parse_pdf_text_to_df(extract_text_from_pdf(find_pdf_file()), language)
    print_df(df)
    return df

def process(df, language):
    # Only allow modules with certain statuses
    df = df[df[LANGUAGE_OPTIONS[language]['status']].isin([LANGUAGE_OPTIONS[language]['passed'], LANGUAGE_OPTIONS[language]['in_progress']])]

    # ECTS
    ects_with_grade = df[LANGUAGE_OPTIONS[language]['ects']].sum()
    df_ects = pd.DataFrame({
        LANGUAGE_OPTIONS[language]['short_description']: [
            LANGUAGE_OPTIONS[language]['required'],
            LANGUAGE_OPTIONS[language]['without_grade'],
            f"{LANGUAGE_OPTIONS[language]['with_grade']} ({len(df)} {LANGUAGE_OPTIONS[language]['grades']})",
            LANGUAGE_OPTIONS[language]['open']
        ],
        LANGUAGE_OPTIONS[language]['ects']: [ECTS_REQUIRED, ECTS_WITHOUT_GRADE, ects_with_grade, ECTS_REQUIRED - (ects_with_grade + ECTS_WITHOUT_GRADE)]
    })
    print_df(df_ects)

    # Overall average
    print(f"\n{LANGUAGE_OPTIONS[language]['overall_average']}: {((df[LANGUAGE_OPTIONS[language]['grade']] * df[LANGUAGE_OPTIONS[language]['ects']]).sum() / ects_with_grade).round(2)}")

    # Information on the individual semesters
    df_semester = df.groupby(LANGUAGE_OPTIONS[language]['semester']).agg({
        LANGUAGE_OPTIONS[language]['grade']: lambda x: (x * df.loc[x.index, LANGUAGE_OPTIONS[language]['ects']]).sum() / df.loc[x.index, LANGUAGE_OPTIONS[language]['ects']].sum(),
        LANGUAGE_OPTIONS[language]['ects']: 'sum'
    }).round(2).reset_index()
    df_semester.columns = [LANGUAGE_OPTIONS[language]['semester'], LANGUAGE_OPTIONS[language]['average'], LANGUAGE_OPTIONS[language]['ects']]
    df_semester = sort_df(df_semester, language=language)
    print_df(df_semester)

    # Number of individual grades
    grade_counts = []
    for grade in [1.0, 1.3, 1.7, 2.0, 2.3, 2.7, 3.0, 3.3, 3.7, 4.0]:
        df_for_grade = df[df[LANGUAGE_OPTIONS[language]['grade']] == grade]
        if not df_for_grade.empty:
            grade_counts.append({LANGUAGE_OPTIONS[language]['grade']: grade, LANGUAGE_OPTIONS[language]['number_of']: len(df_for_grade)})
    df_grade_counts = pd.DataFrame(grade_counts)
    print_df(df_grade_counts)

    # Output modules sorted by semester
    for sem in df[LANGUAGE_OPTIONS[language]["semester"]].unique():
        print(f"\n{sem}:")
        print_df(df[df[LANGUAGE_OPTIONS[language]["semester"]] == sem].drop(
            columns=[LANGUAGE_OPTIONS[language]['semester'],
                     LANGUAGE_OPTIONS[language]['attempt'],
                     LANGUAGE_OPTIONS[language]['status'],
                     LANGUAGE_OPTIONS[language]['remark'],
                     LANGUAGE_OPTIONS[language]['type'],
                     'ArtSortKey']), False)

def main():
    parser = argparse.ArgumentParser(description="Process grades from CSV or PDF files. The script must be executed in the folder in which the CSV or PDF is located!")
    parser.add_argument('--lang', choices=LANGUAGE_OPTIONS.keys(), default='de', help="Select language: 'de' for German, 'en' for English")
    parser.add_argument('--csv', action='store_true', help="Use CSV file")
    parser.add_argument('--pdf', action='store_true', help="Use PDF file")
    args = parser.parse_args()

    if args.csv:
        df = get_df_from_csv()
    # Default: PDF File
    else:
        df = get_df_from_pdf(args.lang)

    # Identify and save entries with NaN in the grade
    removed_entries = df[df[LANGUAGE_OPTIONS[args.lang]['grade']].isna()]

    # Remove entries with NaN from the DataFrame
    df = df.dropna(subset=[LANGUAGE_OPTIONS[args.lang]['grade']])

    # Check and output if NaN is present
    if not removed_entries.empty:
        print(f"\n{LANGUAGE_OPTIONS[args.lang]['not_included_entries']}:")
        print_df(removed_entries)

        ects_without_grade_in_grade_overview = removed_entries[LANGUAGE_OPTIONS[args.lang]['ects']].sum()
        print(f"\n{LANGUAGE_OPTIONS[args.lang]['still_required_ects_without_grade']}: {ECTS_WITHOUT_GRADE} - {ects_without_grade_in_grade_overview} = {ECTS_WITHOUT_GRADE - ects_without_grade_in_grade_overview}")

    # Sort the DataFrame
    df = sort_df(df, args.lang)

    # Create or overwrite the CSV file that may not yet be sorted
    df.drop(columns=['ArtSortKey']).to_csv(CSV_FILE, index=False)

    process(df, args.lang)

if __name__ == "__main__":
    main()