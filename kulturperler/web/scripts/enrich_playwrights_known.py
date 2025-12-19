#!/usr/bin/env python3
"""
Enrich plays with known playwright mappings.
Uses a curated list of well-known plays and their authors.
"""

import sqlite3
import re

DB_PATH = '../static/kulturperler.db'

# Known plays and their authors (Norwegian titles -> Author)
KNOWN_PLAYS = {
    # Ibsen (already done, but for completeness)
    'Vildanden': 'Henrik Ibsen',
    'Gengangere': 'Henrik Ibsen',
    'Gildet paa Solhaug': 'Henrik Ibsen',

    # Strindberg
    'Spöksonaten': 'August Strindberg',
    'Et drømmespill': 'August Strindberg',
    'Fadren': 'August Strindberg',
    'Kammeratene': 'August Strindberg',
    'Kristin': 'August Strindberg',
    'Dödsdansen': 'August Strindberg',

    # Chekhov
    'Kirsebærhagen': 'Anton Tsjekhov',
    'Tre søstre': 'Anton Tsjekhov',
    'Måken': 'Anton Tsjekhov',
    'Onkel Vanja': 'Anton Tsjekhov',
    'Ivanov': 'Anton Tsjekhov',

    # Molière
    'Den innbilt syke': 'Molière',
    'Tartuffe': 'Molière',
    'Den gjerrige': 'Molière',
    'Misantropen': 'Molière',
    'Don Juan': 'Molière',
    'Scapins skøyerstreker': 'Molière',

    # Shakespeare
    'Hamlet': 'William Shakespeare',
    'Macbeth': 'William Shakespeare',
    'Othello': 'William Shakespeare',
    'Kong Lear': 'William Shakespeare',
    'Romeo og Julie': 'William Shakespeare',
    'En midtsommernattsdrøm': 'William Shakespeare',
    'Stormen': 'William Shakespeare',
    'Kjøpmannen i Venedig': 'William Shakespeare',
    'Mye styr for ingenting': 'William Shakespeare',
    'Helligtrekongersaften': 'William Shakespeare',
    'Julius Cæsar': 'William Shakespeare',
    'Richard III': 'William Shakespeare',
    'Henrik IV': 'William Shakespeare',
    'Henrik V': 'William Shakespeare',
    'Troll kan temmes': 'William Shakespeare',

    # Greek classics
    'Antigone': 'Sofokles',
    'Kong Oidipus': 'Sofokles',
    'Elektra': 'Sofokles',
    'Orestien': 'Aiskylos',
    'Medea': 'Evripides',
    'Lysistrata': 'Aristofanes',

    # Modern classics
    'Vente på Godot': 'Samuel Beckett',
    'Mens vi venter på Godot': 'Samuel Beckett',
    'Endgame': 'Samuel Beckett',
    'Glassmenasjeriet': 'Tennessee Williams',
    'En sporvogn til begjær': 'Tennessee Williams',
    'Katten på det varme blikktak': 'Tennessee Williams',
    'Døden for en handelsreisende': 'Arthur Miller',
    'Alle mine sønner': 'Arthur Miller',
    'Heksejakt': 'Arthur Miller',
    'Utsikt fra broen': 'Arthur Miller',
    'Besøk av en gammel dame': 'Friedrich Dürrenmatt',
    'Fysikerne': 'Friedrich Dürrenmatt',
    'Mutter Courage': 'Bertolt Brecht',
    'Mor Courage': 'Bertolt Brecht',
    'Tolvskillingsoperaen': 'Bertolt Brecht',
    'Galileis liv': 'Bertolt Brecht',
    'Den kaukasiske krittringen': 'Bertolt Brecht',

    # Scandinavian
    'Erasmus Montanus': 'Ludvig Holberg',
    'Jeppe på Bjerget': 'Ludvig Holberg',
    'Den politiske kandestøber': 'Ludvig Holberg',
    'Over ævne': 'Bjørnstjerne Bjørnson',
    'Paul Lange og Tora Parsberg': 'Bjørnstjerne Bjørnson',
    'Leonarda': 'Bjørnstjerne Bjørnson',
    'Kongen': 'Bjørnstjerne Bjørnson',
    'Maria Stuart i Skottland': 'Bjørnstjerne Bjørnson',

    # British modern
    'Pygmalion': 'George Bernard Shaw',
    'Candida': 'George Bernard Shaw',
    'Major Barbara': 'George Bernard Shaw',
    'Mrs. Warrens yrke': 'George Bernard Shaw',
    'Androkles og løven': 'George Bernard Shaw',
    'Heartbreak House': 'George Bernard Shaw',
    'Hellige Johanna': 'George Bernard Shaw',
    'Cocktailparty': 'T.S. Eliot',
    'Mordet i katedralen': 'T.S. Eliot',

    # Oscar Wilde
    'Bunbury': 'Oscar Wilde',
    'The Importance of Being Earnest': 'Oscar Wilde',
    'Lady Windermeres vifte': 'Oscar Wilde',
    'Et ideelt ektepar': 'Oscar Wilde',
    'Salomé': 'Oscar Wilde',

    # French
    'Cyrano de Bergerac': 'Edmond Rostand',
    'Den lille prinsen': 'Antoine de Saint-Exupéry',
    'Ingen utgang': 'Jean-Paul Sartre',
    'For lukkede dører': 'Jean-Paul Sartre',
    'Fluene': 'Jean-Paul Sartre',
    'De skitne hender': 'Jean-Paul Sartre',

    # German
    'Woyzeck': 'Georg Büchner',
    'Dantons død': 'Georg Büchner',
    'Faust': 'Johann Wolfgang von Goethe',
    'Don Carlos': 'Friedrich Schiller',
    'Maria Stuart': 'Friedrich Schiller',
    'Wilhelm Tell': 'Friedrich Schiller',
    'Røverne': 'Friedrich Schiller',

    # American
    'Hvem er redd for Virginia Woolf?': 'Edward Albee',
    'Zoo Story': 'Edward Albee',
    'Den amerikanske drøm': 'Edward Albee',
    'Vår lille by': 'Thornton Wilder',
    'På livets vei': 'Thornton Wilder',

    # Russian
    'Revisoren': 'Nikolaj Gogol',
    'Brødrene Karamasov': 'Fjodor Dostojevskij',
    'Forbrytelse og straff': 'Fjodor Dostojevskij',
    'Anna Karenina': 'Leo Tolstoj',

    # Children's classics (often adapted)
    'Peter Pan': 'J.M. Barrie',
    'Alice i Eventyrland': 'Lewis Carroll',
    'Trollmannen fra Oz': 'L. Frank Baum',
    'Snøhvit': 'Brødrene Grimm',
    'Askepott': 'Charles Perrault',
    'Hans og Grete': 'Brødrene Grimm',
    'Den lille havfrue': 'H.C. Andersen',
    'Snødronningen': 'H.C. Andersen',
    'Nøtteknekkeren': 'E.T.A. Hoffmann',

    # Dickens adaptations
    'David Copperfield': 'Charles Dickens',
    'Oliver Twist': 'Charles Dickens',
    'Et juleeventyr': 'Charles Dickens',
    'Store forventninger': 'Charles Dickens',
    'En fortelling om to byer': 'Charles Dickens',

    # Norwegian modern
    'Gift': 'Alexander Kielland',
    'Skipper Worse': 'Alexander Kielland',
    'Garman & Worse': 'Alexander Kielland',
    'Sult': 'Knut Hamsun',
    'Victoria': 'Knut Hamsun',
    'Markens grøde': 'Knut Hamsun',
    'Kristin Lavransdatter': 'Sigrid Undset',
    'Jenny': 'Sigrid Undset',
    'Albertine': 'Christian Krohg',

    # Pinter
    'Vaktmesteren': 'Harold Pinter',
    'Hjemkomsten': 'Harold Pinter',
    'Svik': 'Harold Pinter',
    'Geburtsdagsfesten': 'Harold Pinter',

    # Ionesco
    'Den skallete sangerinnen': 'Eugène Ionesco',
    'Stolene': 'Eugène Ionesco',
    'Neshornene': 'Eugène Ionesco',
    'Leksjonen': 'Eugène Ionesco',

    # Anouilh
    'Antigone': 'Jean Anouilh',  # His version
    'Becket': 'Jean Anouilh',
    'Lerkene': 'Jean Anouilh',

    # Contemporary Norwegian
    'Noen som husker deg': 'Cecilie Løveid',
    'Måkespiserne': 'Cecilie Løveid',
    'Balansedame': 'Cecilie Løveid',
}

def get_or_create_person(cur, name, birth_year=None, death_year=None):
    """Get existing person or create new one."""
    normalized = name.lower().strip()

    cur.execute("SELECT id FROM persons WHERE normalized_name = ?", (normalized,))
    row = cur.fetchone()
    if row:
        return row['id']

    # Create new person
    cur.execute("""
        INSERT INTO persons (name, normalized_name, birth_year, death_year)
        VALUES (?, ?, ?, ?)
    """, (name, normalized, birth_year, death_year))
    return cur.lastrowid

def normalize_title(title):
    """Normalize title for matching."""
    title = re.sub(r'\s*\(\d{4}\)\s*$', '', title)
    title = re.sub(r'\s*-\s*radioteater\s*$', '', title, flags=re.I)
    title = title.strip()
    return title

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Build case-insensitive lookup
    known_lookup = {k.lower(): v for k, v in KNOWN_PLAYS.items()}

    # Get plays without playwright
    cur.execute("SELECT id, title FROM plays WHERE playwright_id IS NULL")
    plays = cur.fetchall()
    print(f"Found {len(plays)} plays without playwright\n")

    updated = 0

    for play in plays:
        play_id = play['id']
        title = play['title']
        norm_title = normalize_title(title).lower()

        if norm_title in known_lookup:
            author = known_lookup[norm_title]
            person_id = get_or_create_person(cur, author)
            cur.execute("UPDATE plays SET playwright_id = ? WHERE id = ?",
                       (person_id, play_id))
            print(f"  {title} -> {author}")
            updated += 1

    conn.commit()
    conn.close()

    print(f"\nUpdated {updated} plays from known mappings")

if __name__ == '__main__':
    main()
