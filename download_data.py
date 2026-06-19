import pandas as pd
from datasets import load_dataset
from pathlib import Path

# 1. Tự động kiểm tra và tạo thư mục đúng cấu trúc dự án CARESCORE-AI của bạn
train_dir = Path("data/processed/positivity/train")
test_dir = Path("data/processed/positivity/test")
train_dir.mkdir(parents=True, exist_ok=True)
test_dir.mkdir(parents=True, exist_ok=True)

print("--- ĐANG TỰ ĐỘNG TẢI VÀ CHUẨN HÓA DATASET THÀNH FILE CSV ---")

try:
    # 2. Tải bộ dữ liệu phân tích cảm xúc tiếng Việt (anotherpolarbear) từ Hugging Face
    dataset = load_dataset("anotherpolarbear/vietnamese-sentiment-analysis")
    
    # 3. Chuyển đổi dữ liệu tải về thành dạng bảng dữ liệu (DataFrame)
    df_train = pd.DataFrame(dataset['train'])
    df_test = pd.DataFrame(dataset['test'])
    
    # 4. Đổi tên cột từ 'comment' thành 'text' cho đúng cấu trúc pipeline của bạn
    df_train = df_train.rename(columns={'comment': 'text'})
    df_test = df_test.rename(columns={'comment': 'text'})
    
    # 5. Hàm quy đổi nhãn: Gốc là số sao (1-5), ta đổi sang chữ (negative, neutral, positive)
    def map_stars_to_sentiment(label):
        if label in [1, 2]:
            return 'negative'
        elif label == 3:
            return 'neutral'
        else:
            return 'positive'
            
    df_train['sentiment'] = df_train['label'].apply(map_stars_to_sentiment)
    df_test['sentiment'] = df_test['label'].apply(map_stars_to_sentiment)
    
    # Lọc giữ lại đúng 2 cột quan trọng nhất như bạn cần
    df_train = df_train[['text', 'sentiment']]
    df_test = df_test[['text', 'sentiment']]
    
    # 6. Xuất trực tiếp thành file CSV sạch vào đúng các folder trong dự án của bạn
    df_train.to_csv(train_dir / "train.csv", index=False, encoding="utf-8-sig")
    df_test.to_csv(test_dir / "test.csv", index=False, encoding="utf-8-sig")
    
    print("\n[THÀNH CÔNG RỰC RỠ!]")
    print(f"- File train.csv đã được tạo tại: {train_dir / 'train.csv'}")
    print(f"- File test.csv đã được tạo tại: {test_dir / 'test.csv'}")
    print("Bây giờ folder dữ liệu của bạn đã sẵn sàng 100% để đem đi train model!")

except Exception as e:
    print(f"\nGặp lỗi hệ thống khi tải: {e}")