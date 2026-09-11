import os
import json
import pandas as pd
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SRC = 'C:/Users/Admin/Downloads/DuLieu/inventory.csv'
DST_DIR = './silver'
os.makedirs(DST_DIR, exist_ok=True)


def strip_strings(df: pd.DataFrame) -> pd.DataFrame:
    """Trim khoảng trắng thừa ở mọi cột kiểu chuỗi."""
    obj_cols = df.select_dtypes(include=['object', 'string']).columns
    for c in obj_cols:
        df[c] = df[c].astype(str).str.strip()
    return df


def clean_inventory(src_path: str) -> tuple[pd.DataFrame, dict]:
    report = {}

    df = pd.read_csv(src_path, encoding='utf-8-sig')
    n_raw = len(df)

    df = strip_strings(df)

    # Chuẩn hoá kiểu dữ liệu
    df['snapshot_date'] = pd.to_datetime(df['snapshot_date'], errors='coerce').dt.date

    int_cols = ['product_id', 'stock_on_hand', 'units_received', 'units_sold',
                'stockout_days', 'stockout_flag', 'overstock_flag', 'reorder_flag',
                'year', 'month']
    for c in int_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce').astype('Int64')

    float_cols = ['days_of_supply', 'fill_rate', 'sell_through_rate']
    for c in float_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce')

    # Các tỷ lệ (rate) phải nằm trong khoảng [0, 1] -> clip phòng trường hợp lỗi nhập liệu
    fill_out = ((df['fill_rate'] < 0) | (df['fill_rate'] > 1)).sum()
    df['fill_rate'] = df['fill_rate'].clip(0, 1)

    str_out = ((df['sell_through_rate'] < 0) | (df['sell_through_rate'] > 1)).sum()
    df['sell_through_rate'] = df['sell_through_rate'].clip(0, 1)

    # year / month phải nhất quán với snapshot_date -> tính lại từ snapshot_date
    snap_dt = pd.to_datetime(df['snapshot_date'])
    mismatch_ym = ((df['year'] != snap_dt.dt.year) | (df['month'] != snap_dt.dt.month)).sum()
    df['year'] = snap_dt.dt.year
    df['month'] = snap_dt.dt.month

    # Loại bỏ dòng trùng lặp hoàn toàn
    dup_full = df.duplicated().sum()
    df = df.drop_duplicates()

    # Loại bỏ trùng khóa nghiệp vụ (snapshot_date, product_id)
    dup_key = df.duplicated(subset=['snapshot_date', 'product_id']).sum()
    df = df.drop_duplicates(subset=['snapshot_date', 'product_id'], keep='first')

    report = {
        'rows_raw': n_raw,
        'rows_silver': len(df),
        'full_duplicate_rows_removed': int(dup_full),
        'duplicate_snapshot_product_removed': int(dup_key),
        'fill_rate_out_of_range_clipped': int(fill_out),
        'sell_through_rate_out_of_range_clipped': int(str_out),
        'year_month_mismatch_fixed': int(mismatch_ym),
    }
    return df, report


if __name__ == '__main__':
    print('Đang làm sạch inventory.csv ...')
    df_clean, report = clean_inventory(SRC)

    out_csv = os.path.join(DST_DIR, 'inventory_silver.csv')
    df_clean.to_csv(out_csv, index=False, encoding='utf-8-sig')

    out_report = os.path.join(DST_DIR, 'inventory_quality_report.json')
    with open(out_report, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f'Đã lưu: {out_csv}')
