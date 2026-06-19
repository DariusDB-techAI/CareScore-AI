
# Hướng dẫn gán nhãn lại dữ liệu CSKH theo 5 tiêu chí

## 1. sentiment_label / sentiment_score
Đánh giá cảm xúc tổng thể của cuộc hội thoại.

Gợi ý nhãn:
- negative
- neutral
- positive

Gợi ý score:
- 1: rất tiêu cực
- 2: tiêu cực
- 3: trung lập
- 4: tích cực
- 5: rất tích cực

## 2. empathy_label / empathy_score
Đánh giá mức độ đồng cảm của nhân viên.

Gợi ý nhãn:
- no_empathy
- low_empathy
- medium_empathy
- high_empathy

Gợi ý score:
- 1: không đồng cảm
- 2: ít đồng cảm
- 3: có đồng cảm nhưng còn chung chung
- 4: đồng cảm rõ
- 5: đồng cảm rất tốt, phản hồi đúng cảm xúc khách hàng

## 3. politeness_label / politeness_score
Đánh giá sự lịch sự và tôn trọng.

Gợi ý nhãn:
- impolite
- neutral
- polite
- very_polite

Gợi ý score:
- 1: bất lịch sự
- 2: hơi thiếu lịch sự
- 3: trung lập
- 4: lịch sự
- 5: rất lịch sự, chuyên nghiệp

## 4. toxicity_label / toxicity_score
Đánh giá ngôn ngữ tiêu cực hoặc công kích.

Gợi ý nhãn:
- clean
- negative
- offensive
- hate

Gợi ý score:
- 0: không có độc hại/công kích
- 1: tiêu cực nhẹ
- 2: công kích/xúc phạm
- 3: thù ghét/nghiêm trọng

## 5. resolution_label / resolution_score
Đánh giá khả năng giải quyết vấn đề.

Gợi ý nhãn:
- unresolved
- partially_resolved
- resolved

Gợi ý score:
- 1: không giải quyết
- 2: có phản hồi nhưng không có hướng xử lý rõ
- 3: có hướng xử lý một phần
- 4: giải quyết khá tốt
- 5: giải quyết đầy đủ, khách hàng có thể tiếp tục hành động rõ ràng
