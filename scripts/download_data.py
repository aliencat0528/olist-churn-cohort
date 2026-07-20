"""下載 Olist 資料集到 data/。

優先用 Kaggle API（需 ~/.kaggle/kaggle.json，見 README「快速開始」）；
沒有憑證時印出手動下載指引。
"""

import subprocess
import sys
import zipfile
from pathlib import Path

DATASET = 'olistbr/brazilian-ecommerce'
DATA_DIR = Path(__file__).resolve().parents[1] / 'data'

EXPECTED_FILES = [
    'olist_orders_dataset.csv',
    'olist_customers_dataset.csv',
    'olist_order_items_dataset.csv',
    'olist_order_payments_dataset.csv',
    'olist_order_reviews_dataset.csv',
    'olist_products_dataset.csv',
    'olist_sellers_dataset.csv',
    'olist_geolocation_dataset.csv',
    'product_category_name_translation.csv',
]


def already_downloaded() -> bool:
    return all((DATA_DIR / f).exists() for f in EXPECTED_FILES)


def main() -> int:
    DATA_DIR.mkdir(exist_ok=True)
    if already_downloaded():
        print(f'data/ 已有全部 {len(EXPECTED_FILES)} 個 CSV，跳過下載')
        return 0

    kaggle_json = Path.home() / '.kaggle' / 'kaggle.json'
    if not kaggle_json.exists():
        print('找不到 ~/.kaggle/kaggle.json。兩種方式擇一：')
        print('  a) kaggle.com → Settings → Create New Token，把 kaggle.json 放到 ~/.kaggle/')
        print('     然後重跑本 script')
        print(f'  b) 手動從 https://www.kaggle.com/datasets/{DATASET} 下載 zip，解壓到 data/')
        return 1

    try:
        subprocess.run(
            [sys.executable, '-m', 'kaggle', 'datasets', 'download',
             '-d', DATASET, '-p', str(DATA_DIR)],
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f'Kaggle 下載失敗：{e}')
        print('請先 pip install kaggle，或改用手動下載（見 README）')
        return 1

    for z in DATA_DIR.glob('*.zip'):
        with zipfile.ZipFile(z) as f:
            f.extractall(DATA_DIR)
        z.unlink()

    missing = [f for f in EXPECTED_FILES if not (DATA_DIR / f).exists()]
    if missing:
        print(f'解壓後仍缺檔案：{missing}')
        return 1
    print('下載完成，9 個 CSV 就緒')
    return 0


if __name__ == '__main__':
    sys.exit(main())
