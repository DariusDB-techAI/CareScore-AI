# Dataset Collection theo mục đích sử dụng

Dữ liệu được chia thành 3 nhóm chính:

## 1. main_train

Dataset chính để train thật.

Ưu tiên:
- Tiếng Việt.
- Có nhãn rõ.
- Gần đúng tiêu chí cần đánh giá.
- Có thể dùng trực tiếp cho supervised learning.

Ví dụ:
- Sentiment tiếng Việt.
- Toxicity/hate speech tiếng Việt.

## 2. auxiliary_pretrain_baseline

Dataset phụ để pretrain hoặc làm baseline.

Đặc điểm:
- Có thể là tiếng Anh.
- Có thể lệch domain so với CSKH.
- Vẫn hữu ích để học biểu hiện đồng cảm, lịch sự, hoặc độc hại.

Ví dụ:
- EmpatheticDialogues.
- ESConv.
- Stanford Politeness.
- Polite Guard.

## 3. needs_relabel

Dataset cần gán nhãn lại.

Đặc điểm:
- Gần domain hội thoại, customer support hoặc task-oriented dialogue.
- Chưa có đủ 5 nhãn theo bài toán.
- Cần gán lại theo rubric của dự án.

Ví dụ:
- TweetSumm.
- MultiWOZ.
- Customer Support on Twitter.
- Vietnamese Customer Support QA.
- Dữ liệu CSKH tiếng Việt tự thu thập.

## 5 tiêu chí đánh giá

1. 01_sentiment_overall
2. 02_empathy
3. 03_politeness_respect
4. 04_negative_attack_toxicity
5. 05_problem_resolution

## Khuyến nghị train model

### Sentiment
Dùng main_train trước:
- vietnamese_sentiment_analysis
- UIT-VSFC

### Toxicity
Dùng main_train trước:
- ViHSD
- ViCTSD

### Empathy
Dùng auxiliary trước để baseline:
- EmpatheticDialogues
- ESConv

Sau đó gán nhãn lại dữ liệu CSKH tiếng Việt.

### Politeness
Dùng auxiliary trước để baseline:
- Stanford Politeness
- Polite Guard

Sau đó gán nhãn lại dữ liệu CSKH tiếng Việt.

### Problem Resolution
Không nên train trực tiếp từ MultiWOZ/TweetSumm nếu chưa gán nhãn lại.
Nên dùng needs_relabel và tạo nhãn:
- unresolved
- partially_resolved
- resolved

Hoặc score 1-5.