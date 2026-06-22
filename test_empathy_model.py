"""
Quick test script for empathy model.
Run: python test_empathy_model.py
"""
import json
from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

MODEL_DIR = Path("models/empathy_xlm_roberta_anhnhc/final_model")
MAX_LENGTH = 512

TEST_CASES = [
    {
        "label": "low_empathy",
        "text": """Khach hang: Tôi vừa thanh toán xong thấy bị trừ tiền 2 lần, giải thích đi.
Nhan vien: Dạ anh cho em xem mã giao dịch ạ.
Khach hang: Không có mã gì hết, thẻ tôi bị trừ 2 lần là sự thật.
Nhan vien: Dạ bên em chỉ ghi nhận 1 giao dịch thành công, nếu bị trừ 2 lần thì do ngân hàng pending ạ. Anh liên hệ ngân hàng để được xác minh.
Khach hang: Tôi hỏi bên anh chứ sao lại đẩy sang ngân hàng?
Nhan vien: Dạ bên em không can thiệp được vào hệ thống ngân hàng ạ. Anh phải làm việc trực tiếp với ngân hàng để được hoàn tiền.
Khach hang: Thôi kệ, tôi tự xử lý được.""",
    },
    {
        "label": "low_empathy",
        "text": """Khach hang: Laptop tôi mua hôm qua về cắm sạc không nhận, hàng lỗi từ hộp rồi.
Nhan vien: Dạ anh thử cắm cổng khác chưa ạ?
Khach hang: Thử hết rồi. Anh đừng hỏi tôi thử cái này cái kia nữa, máy lỗi thì đổi cho tôi đi.
Nhan vien: Dạ máy cần được kiểm tra trước khi đổi ạ, anh mang vào cửa hàng để kỹ thuật xem.
Khach hang: Mua về 1 ngày mà còn phải kiểm tra gì nữa? Cửa hàng các anh toàn làm khó khách.
Nhan vien: Dạ đây là quy trình bắt buộc ạ, em không thể bỏ qua bước này được.
Khach hang: Thôi tôi lên mạng review cho mọi người biết.""",
    },
    {
        "label": "medium_empathy",
        "text": """Khach hang: Tôi đặt bộ loa để kịp sinh nhật vợ tối nay, giờ 3 giờ chiều rồi shipper không liên lạc gì hết, rất bực.
Nhan vien: Dạ anh cho em mã đơn để em kiểm tra tình trạng ạ.
Khach hang: ORD-6621. Tôi cần kịp trước 6 giờ để setup.
Nhan vien: Dạ em thấy đơn rồi, shipper dự kiến giao lúc 4 đến 5 giờ ạ. Anh để lại số điện thoại để shipper liên hệ trước.
Khach hang: 5 giờ thì kịp không? Setup mất ít nhất 30 phút.
Nhan vien: Dạ em nhắn shipper ưu tiên giao trước 4 giờ 30 cho anh ạ.
Khach hang: Được rồi. Lần sau ghi rõ giờ giao ước tính đi để khách chủ động.
Nhan vien: Dạ em ghi nhận ạ.
Khach hang: Oke.""",
    },
    {
        "label": "medium_empathy",
        "text": """Khach hang: Tai nghe tôi mua về dùng thấy noise cancelling không hoạt động, quảng cáo sai.
Nhan vien: Dạ anh đang dùng trong môi trường nào ạ?
Khach hang: Quán cà phê. Tiếng ồn vẫn lọt vào rõ ràng dù tôi bật hết rồi.
Nhan vien: Dạ tính năng noise cancelling chủ động cần giữ nút giữa 2 giây để kích hoạt, mặc định tắt ạ.
Khach hang: Ủa tôi không biết điều đó, thử xem.
Nhan vien: Dạ anh thử rồi thấy khác không ạ?
Khach hang: Ừ khác rồi. Nhưng cái này nên ghi rõ trong hộp.
Nhan vien: Dạ em ghi nhận ạ.
Khach hang: Thôi được.""",
    },
    {
        "label": "high_empathy",
        "text": """Khach hang: Tôi mua cái điện thoại này 2 triệu để làm quà sinh nhật 18 tuổi cho con gái, nó chưa dùng được 1 ngày đã chết nguồn rồi. Bán hàng kiểu gì vậy, con bé khóc cả buổi tối.
Nhan vien: Dạ em xin lỗi anh và cháu rất nhiều. Sinh nhật 18 tuổi mà quà bị hỏng ngay ngày đầu thì thật sự rất đáng tiếc, em hoàn toàn hiểu cảm giác của anh lúc này ạ.
Khach hang: Đáng tiếc là nhẹ, tôi tức lắm. Con tôi chờ cả tháng mới có quà, giờ lại thế này.
Nhan vien: Dạ anh tức là đúng rồi ạ, không ai chấp nhận điều này được hết. Anh cho em xem hóa đơn, em sẽ xử lý đổi máy mới ngay hôm nay ạ.
Khach hang: Hóa đơn đây. Nhưng giờ cửa hàng còn hàng không?
Nhan vien: Dạ em kiểm tra ngay — còn đúng model và màu đó ạ, em đặt giữ cho anh luôn.
Khach hang: Thật không? Vậy thì may. Thôi anh hiểu lỗi này do sản xuất chứ cửa hàng không cố tình, nhưng lần sau kiểm tra kỹ trước khi bán đi.
Nhan vien: Dạ anh nói hoàn toàn có lý. Em xin lỗi vì cháu phải trải qua đêm sinh nhật không trọn vẹn.
Khach hang: Ừ thôi cảm ơn em đã xử lý nhanh, may mà gọi đúng người.
Nhan vien: Dạ em rất vui được hỗ trợ anh và cháu. Chúc cháu sinh nhật vui vẻ ạ.""",
    },
    {
        "label": "high_empathy",
        "text": """Khach hang: Tôi đặt máy tính bảng cho con học online, giao về hỏng màn hình, tôi gọi 3 lần không ai nghe, giờ con tôi không có máy học bài, thầy giáo nhắn tin hỏi liên tục.
Nhan vien: Dạ em nghe rõ ạ. Chị vừa giao hàng hỏng, lại không liên hệ được mấy lần, con đang cần máy để học — dồn vào một lúc như vậy thì ai cũng căng thẳng lắm. Em xin lỗi chị vì bên em đã để chị chờ lâu đến vậy ạ.
Khach hang: Xin lỗi thì được gì, tôi cần máy cho con học ngay hôm nay.
Nhan vien: Dạ em hiểu, hôm nay là yêu cầu tối thiểu. Chị cho em mã đơn, em xử lý đổi máy và giao lại trong hôm nay, nếu kho gần còn hàng em ưu tiên giao trong 2 giờ.
Khach hang: ORD-9981. 2 tiếng được không? Thầy nhắn lúc 3 giờ chiều là phải có mặt học.
Nhan vien: Dạ kho cách chị 4km còn hàng, shipper có thể đến trước 2 giờ 30 ạ. Em đặt lịch và gửi chị số shipper luôn.
Khach hang: Vậy thì được. Tôi không muốn con bị ảnh hưởng việc học vì lỗi của người khác.
Nhan vien: Dạ chị nói đúng ạ, đây hoàn toàn là lỗi của bên em. Em đã gửi số shipper rồi ạ.
Khach hang: Cảm ơn em, lần này em xử lý được. Hồi nãy tôi nóng quá nói nặng lời, thông cảm nhé.
Nhan vien: Dạ không sao ạ, chị lo cho con là điều hoàn toàn tự nhiên. Chúc con học tốt ạ.""",
    },
]

SCORE_MAP = {"low_empathy": 1, "medium_empathy": 3, "high_empathy": 5}


def load_model(model_dir: Path):
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)
    model.eval()
    label_mapping = json.loads((model_dir / "label_mapping.json").read_text())
    id2label = {int(k): v for k, v in label_mapping["id2label"].items()}
    return tokenizer, model, id2label


def predict(text: str, tokenizer, model, id2label: dict) -> tuple[str, float]:
    device = next(model.parameters()).device
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=MAX_LENGTH)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        logits = model(**inputs).logits
    probs = torch.softmax(logits, dim=-1)[0]
    pred_id = int(torch.argmax(logits, dim=-1).item())
    return id2label[pred_id], float(probs[pred_id])


def main():
    if not (MODEL_DIR / "config.json").exists():
        print(f"Model not found at {MODEL_DIR}. Run the training notebook first.")
        return

    print(f"Loading model from {MODEL_DIR}...")
    tokenizer, model, id2label = load_model(MODEL_DIR)
    print(f"Model loaded. Labels: {id2label}\n")

    passed = 0
    print(f"{'#':<4} {'Expected':<18} {'Predicted':<18} {'Conf':>6}  Result")
    print("-" * 60)
    for i, tc in enumerate(TEST_CASES, 1):
        pred_label, conf = predict(tc["text"], tokenizer, model, id2label)
        ok = pred_label == tc["label"]
        passed += ok
        status = "PASS" if ok else "FAIL"
        print(f"{i:<4} {tc['label']:<18} {pred_label:<18} {conf:>6.2%}  {status}")

    total = len(TEST_CASES)
    print("-" * 60)
    print(f"\nResult: {passed}/{total} passed")

    if passed == total:
        print("Model is demo-ready.")
    elif passed >= total * 0.67:
        print("Partial fit — re-run training with more epochs.")
    else:
        print("Model needs retraining. Check notebook cell-13 parameters.")


if __name__ == "__main__":
    main()