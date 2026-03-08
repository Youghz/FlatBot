"""Google Sheets integration for storing and tracking listings."""

import logging
from datetime import date, datetime

import google.auth
import gspread

logger = logging.getLogger(__name__)


def _sanitize_cell(value: str) -> str:
    """Prevent formula injection in Google Sheets.

    Sheets interprets cells starting with =, +, -, @ as formulas.
    Prefix with a single quote to force text interpretation.
    """
    if isinstance(value, str) and value and value[0] in ("=", "+", "-", "@"):
        return f"'{value}"
    return value


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = [
    "ID",
    "Source",
    "Titre",
    "Prix ($)",
    "Chambres",
    "Adresse",
    "Quartier",
    "Meuble",
    "Parking",
    "URL",
    "Date ajout",
    "Emmenagement",
    "Description",
]


def _get_client(config: dict) -> gspread.Client:
    credentials, project = google.auth.default(scopes=SCOPES)
    return gspread.authorize(credentials)


def _get_or_create_spreadsheet(client: gspread.Client, config: dict) -> gspread.Spreadsheet:
    name = config["google_sheets"]["spreadsheet_name"]
    spreadsheet_id = config["google_sheets"].get("spreadsheet_id", "")

    # If we have a known spreadsheet ID, open it directly
    if spreadsheet_id:
        try:
            spreadsheet = client.open_by_key(spreadsheet_id)
            logger.info(f"Opened spreadsheet by ID: {spreadsheet_id}")
        except gspread.exceptions.APIError as e:
            logger.error(f"Cannot open spreadsheet {spreadsheet_id}: {e}")
            raise
    else:
        try:
            spreadsheet = client.open(name)
            logger.info(f"Opened existing spreadsheet: {name}")
        except gspread.SpreadsheetNotFound:
            spreadsheet = client.create(name)
            spreadsheet.share("", perm_type="anyone", role="reader")
            logger.info(f"Created new spreadsheet: {name}")
            logger.info(f"Add this to config.yaml -> google_sheets.spreadsheet_id: {spreadsheet.id}")

    sheet = spreadsheet.sheet1

    # Ensure headers exist
    existing = sheet.row_values(1) if sheet.row_count > 0 else []
    if existing != HEADERS:
        sheet.clear()
        sheet.append_row(HEADERS)
        sheet.format("1:1", {"textFormat": {"bold": True}})
        logger.info("Headers initialized")

    return spreadsheet


def get_existing_ids(config: dict) -> set[str]:
    """Return all listing IDs already in the sheet."""
    client = _get_client(config)
    spreadsheet = _get_or_create_spreadsheet(client, config)
    sheet = spreadsheet.sheet1

    all_values = sheet.col_values(1)  # Column A = IDs
    # Skip header
    return set(all_values[1:]) if len(all_values) > 1 else set()


def add_listings(listings: list, config: dict) -> tuple[list, str]:
    """Add new listings to the Google Sheet.

    Returns (new_listings, spreadsheet_url).
    """
    client = _get_client(config)
    spreadsheet = _get_or_create_spreadsheet(client, config)
    sheet = spreadsheet.sheet1

    existing_ids = set(sheet.col_values(1)[1:]) if sheet.row_count > 1 else set()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    new_listings = []
    rows_to_add = []

    for listing in listings:
        if listing.listing_id in existing_ids:
            continue

        row = [
            _sanitize_cell(listing.listing_id),
            _sanitize_cell(listing.source),
            _sanitize_cell(listing.title),
            listing.price,
            listing.bedrooms,
            _sanitize_cell(listing.address),
            _sanitize_cell(listing.neighbourhood),
            "Oui" if listing.furnished else "Non",
            "Oui" if listing.parking else "Non",
            listing.url,
            now,
            listing.move_in_date or "",
            _sanitize_cell(listing.description[:200]),
        ]
        rows_to_add.append(row)
        new_listings.append(listing)

    if rows_to_add:
        sheet.append_rows(rows_to_add, value_input_option="USER_ENTERED")
        logger.info(f"Added {len(rows_to_add)} new listings to sheet")

    url = spreadsheet.url

    # Clean up listings with past move-in dates
    _remove_expired_listings(sheet)

    return new_listings, url


def _remove_expired_listings(sheet) -> None:
    """Remove rows where the move-in date is in the past."""
    try:
        all_rows = sheet.get_all_values()
    except Exception as e:
        logger.warning(f"Could not read sheet for cleanup: {e}")
        return

    if len(all_rows) <= 1:
        return

    headers = all_rows[0]
    try:
        date_col = headers.index("Emmenagement")
    except ValueError:
        return

    today = date.today()
    rows_to_delete = []

    # Iterate from bottom to top so row indices stay valid during deletion
    for i in range(len(all_rows) - 1, 0, -1):
        row = all_rows[i]
        if date_col >= len(row):
            continue
        move_in = row[date_col].strip()
        if not move_in or move_in == "immediate":
            continue
        try:
            move_in_date = datetime.strptime(move_in, "%Y-%m-%d").date()
            if move_in_date < today:
                rows_to_delete.append(i + 1)  # 1-indexed for Sheets API
        except ValueError:
            continue

    if rows_to_delete:
        for row_num in rows_to_delete:
            sheet.delete_rows(row_num)
        logger.info(f"Removed {len(rows_to_delete)} expired listings from sheet")
