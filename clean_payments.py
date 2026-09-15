import os
import json
import pandas as pd
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SRC = 'C:/Users/Admin/Downloads/DuLieu/payments.csv'
DST_DIR = './silver'
os.makedirs(DST_DIR, exist_ok=True)


def strip_strings(df: pd.DataFrame) -> pd.DataFrame:
    """Trim khoảng trắng thừa ở mọi cột kiểu chuỗi."""
    obj_cols = df.select_dtypes(include=['object', 'string']).columns
    for c in obj_cols:
        df[c] = df[c].astype(str).str.strip()
    return df


def clean_payments(src_path: str) -> tuple[pd.DataFrame, dict]:
    report = {}

    df = pd.read_csv(src_path, encoding='utf-8-sig')
    n_raw = len(df)

    df = strip_strings(df)

    # Chuẩn hoá kiểu dữ liệu
    df['order_id'] = pd.to_numeric(df['order_id'], errors='coerce').astype('Int64')
    df['installments'] = pd.to_numeric(df['installments'], errors='coerce').astype('Int64')
    df['payment_value'] = pd.to_numeric(df['payment_value'], errors='coerce')

    # Loại bỏ giá trị phi lý: số tiền và số kỳ trả góp phải dương
    bad_val = (df['payment_value'] <= 0).sum()
    bad_inst = (df['installments'] <= 0).sum()
    df = df[(df['payment_value'] > 0) & (df['installments'] > 0)]

    # Loại bỏ dòng trùng lặp hoàn toàn
    dup_full = df.duplicated().sum()
    df = df.drop_duplicates()

    # Loại bỏ trùng khóa order_id (mỗi đơn hàng chỉ có 1 bản ghi thanh toán)
    dup_key = df.duplicated(subset=['order_id']).sum()
    df = df.drop_duplicates(subset=['order_id'], keep='first')

    report = {
        'rows_raw': n_raw,
        'rows_silver': len(df),
        'full_duplicate_rows_removed': int(dup_full),
        'duplicate_order_id_removed': int(dup_key),
        'invalid_payment_value_removed': int(bad_val),
        'invalid_installments_removed': int(bad_inst),
    }
    return df, report


if __name__ == '__main__':
    print('Đang làm sạch payments.csv ...')
    df_clean, report = clean_payments(SRC)

    out_csv = os.path.join(DST_DIR, 'payments_silver.csv')
    df_clean.to_csv(out_csv, index=False, encoding='utf-8-sig')

    out_report = os.path.join(DST_DIR, 'payments_quality_report.json')
    with open(out_report, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f'Đã lưu: {out_csv}')
