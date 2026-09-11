import os
import json
import numpy as np
import pandas as pd
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SRC = 'C:/Users/Admin/Downloads/DuLieu/order_items.csv'
DST_DIR = './silver'
os.makedirs(DST_DIR, exist_ok=True)


def strip_strings(df: pd.DataFrame) -> pd.DataFrame:
    """Trim khoảng trắng thừa ở mọi cột kiểu chuỗi."""
    obj_cols = df.select_dtypes(include=['object', 'string']).columns
    for c in obj_cols:
        df[c] = df[c].astype(str).str.strip()
    return df


def first_notna(s: pd.Series):
    s = s.dropna()
    return s.iloc[0] if len(s) else np.nan


def clean_order_items(src_path: str) -> tuple[pd.DataFrame, dict]:
    report = {}

    df = pd.read_csv(src_path, encoding='utf-8-sig', low_memory=False)
    n_raw = len(df)

    df = strip_strings(df)
    # strip_strings ép cả cột có NaN (promo_id/promo_id_2) thành chuỗi "nan" -> khôi phục null
    df['promo_id'] = df['promo_id'].replace({'nan': np.nan, '': np.nan})
    df['promo_id_2'] = df['promo_id_2'].replace({'nan': np.nan, '': np.nan})

    # Chuẩn hoá kiểu dữ liệu
    for c in ['order_id', 'product_id', 'quantity']:
        df[c] = pd.to_numeric(df[c], errors='coerce').astype('Int64')
    for c in ['unit_price', 'discount_amount']:
        df[c] = pd.to_numeric(df[c], errors='coerce')

    # Loại bỏ giá trị phi lý: số lượng/đơn giá phải dương, chiết khấu không âm
    # và không được vượt quá tổng giá trị dòng hàng
    bad_qty = (df['quantity'] <= 0).sum()
    bad_price = (df['unit_price'] <= 0).sum()
    bad_disc = (
        (df['discount_amount'] < 0).sum()
        + (df['discount_amount'] > df['unit_price'] * df['quantity']).sum()
    )
    df = df[(df['quantity'] > 0) & (df['unit_price'] > 0) & (df['discount_amount'] >= 0)]

    # Loại bỏ dòng trùng lặp hoàn toàn
    dup_full = df.duplicated().sum()
    df = df.drop_duplicates()

    # Gộp các dòng trùng khóa nghiệp vụ (order_id, product_id) thành 1 dòng
    # (cùng 1 sản phẩm bị ghi thành nhiều dòng trong cùng 1 đơn hàng)
    dup_key_rows = df.duplicated(subset=['order_id', 'product_id'], keep=False).sum()
    df['_line_amount_tmp'] = df['unit_price'] * df['quantity']

    agg = df.groupby(['order_id', 'product_id'], as_index=False).agg(
        quantity=('quantity', 'sum'),
        unit_price_weighted_sum=('_line_amount_tmp', 'sum'),
        discount_amount=('discount_amount', 'sum'),
        promo_id=('promo_id', first_notna),
        promo_id_2=('promo_id_2', first_notna),
    )
    # Đơn giá sau gộp = bình quân gia quyền theo số lượng
    agg['unit_price'] = (agg['unit_price_weighted_sum'] / agg['quantity']).round(2)
    # Cột tính toán bổ sung, phục vụ đối chiếu doanh thu ở tầng Gold
    agg['line_amount'] = (agg['unit_price'] * agg['quantity'] - agg['discount_amount']).round(2)
    agg = agg.drop(columns=['unit_price_weighted_sum'])
    agg = agg[['order_id', 'product_id', 'quantity', 'unit_price', 'discount_amount',
               'promo_id', 'promo_id_2', 'line_amount']]

    report = {
        'rows_raw': n_raw,
        'rows_silver': len(agg),
        'full_duplicate_rows_removed': int(dup_full),
        'rows_involved_in_key_duplicates_merged': int(dup_key_rows),
        'invalid_quantity_removed': int(bad_qty),
        'invalid_unit_price_removed': int(bad_price),
        'invalid_discount_removed': int(bad_disc),
    }
    return agg, report


if __name__ == '__main__':
    print('Đang làm sạch order_items.csv ...')
    df_clean, report = clean_order_items(SRC)

    out_csv = os.path.join(DST_DIR, 'order_items_silver.csv')
    df_clean.to_csv(out_csv, index=False, encoding='utf-8-sig')

    out_report = os.path.join(DST_DIR, 'order_items_quality_report.json')
    with open(out_report, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f'Đã lưu: {out_csv}')
