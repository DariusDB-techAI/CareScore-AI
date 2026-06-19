# Dataset Collection cho hệ thống đánh giá chất lượng hội thoại

Dữ liệu được chia theo 5 tiêu chí đánh giá chính.

## 01_sentiment_overall

Dữ liệu phục vụ đánh giá cảm xúc tổng thể của cuộc hội thoại.

Dataset chính:
- anotherpolarbear/vietnamese-sentiment-analysis

## 02_empathy

Dữ liệu phục vụ đánh giá mức độ đồng cảm của nhân viên.

Dataset chính:
- EmpatheticDialogues

Lưu ý:
- Không dùng load_dataset('facebook/empathetic_dialogues') vì lỗi dataset script cũ.
- Script hiện tại tải trực tiếp từ CSV mirror.
- CSV được đọc bằng engine='python' và on_bad_lines='skip'.

## 03_politeness_respect

Dữ liệu phục vụ đánh giá sự lịch sự và tôn trọng.

Dataset chính:
- Cleanlab/stanford-politeness

Lưu ý:
- Dataset này được tải từng file CSV riêng lẻ.
- Không dùng load_dataset trực tiếp trên toàn bộ repo vì dễ lỗi schema mismatch.

## 04_negative_attack_toxicity

Dữ liệu phục vụ phát hiện ngôn ngữ tiêu cực, công kích, xúc phạm.

Dataset chính:
- uitnlp/vihsd
- phusroyal/ViHOS

## 05_problem_resolution

Dữ liệu phục vụ đánh giá khả năng giải quyết vấn đề trong hội thoại CSKH.

Dataset chính:
- pfb30/multi_woz_v22
- ura-hcmut/Vietnamese-Customer-Support-QA
- TweetSumm từ GitHub
- Customer Support on Twitter từ Kaggle, cần tải thủ công

## Lưu ý quan trọng

- Không phải dataset nào cũng có nhãn đúng 100% theo bài toán của bạn.
- Sentiment và toxicity có thể train khá trực tiếp.
- Empathy, politeness và problem resolution nên được dùng làm dữ liệu nền hoặc baseline.
- Với bài toán cuối cùng, nên tự gán nhãn thêm một tập hội thoại CSKH tiếng Việt theo 5 tiêu chí.
