import os
import json
import pandas as pd
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SRC = 'C:/Users/Admin/Downloads/DuLieu/orders_enriched.csv'
DST_DIR = './silver'
os.makedirs(DST_DIR, exist_ok=True)


def strip_strings(df: pd.DataFrame) -> pd.DataFrame:
    obj_cols = df.select_dtypes(include=['object', 'string']).columns
    for c in obj_cols:
        df[c] = df[c].astype(str).str.strip()
    return df


def clean_orders_enriched(src_path: str) -> tuple[pd.DataFrame, dict]:
    report = {}
    df = pd.read_csv(src_path, encoding='utf-8-sig', dtype={'zip': str})
    n_raw = len(df)

    df = strip_strings(df)
    df['order_date'] = pd.to_datetime(df['order_date'], errors='coerce').dt.date
    df['zip'] = df['zip'].str.zfill(5)  # chuẩn hoá mã zip về 5 chữ số
    for c in ['order_id', 'customer_id', 'years_experience']:
        df[c] = pd.to_numeric(df[c], errors='coerce').astype('Int64')
    dup_full = df.duplicated().sum()
    df = df.drop_duplicates()
    dup_key = df.duplicated(subset=['order_id']).sum()
    df = df.drop_duplicates(subset=['order_id'], keep='first')
    bad_dates = df['order_date'].isna().sum()
    df = df[df['order_date'].notna()]

    report = {
        'rows_raw': n_raw,
        'rows_silver': len(df),
        'full_duplicate_rows_removed': int(dup_full),
        'duplicate_order_id_removed': int(dup_key),
        'invalid_order_date_removed': int(bad_dates),
    }
    return df, report


if __name__ == '__main__':
    print('Đang làm sạch orders_enriched.csv ...')
    df_clean, report = clean_orders_enriched(SRC)

    out_csv = os.path.join(DST_DIR, 'orders_enriched_silver.csv')
    df_clean.to_csv(out_csv, index=False, encoding='utf-8-sig')

    out_report = os.path.join(DST_DIR, 'orders_enriched_quality_report.json')
    with open(out_report, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f'Đã lưu: {out_csv}')
