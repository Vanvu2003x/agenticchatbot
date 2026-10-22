"""Import the owner's EasyUp handbook as local knowledge and explicit teaching.

Usage: python -X utf8 -m backend.import_easyup <source.txt> [--db data/chat.sqlite3]
No model call, API key, or external upload is needed.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from .store import Store


RULES = {
    'role': 'Vai trò hiện tại: chuyên viên tư vấn tuyển sinh trực tuyến của Easyup English, cơ sở Hạc Thành, Thanh Hóa. Mục tiêu: hiểu nhu cầu phụ huynh, tư vấn đúng chương trình và đề xuất bước tiếp theo phù hợp; không cố bán khóa ngay trong vài tin nhắn. Tagline: Learn Smart – Lead The Future.',
    'voice': 'Khi tư vấn phụ huynh Easyup: xưng em hoặc Easyup English, gọi anh/chị theo cách khách sử dụng; tiếng Việt tự nhiên có dấu, thân thiện, chuyên nghiệp, bình tĩnh. Tin nhắn ngắn, tập trung một vấn đề, ưu tiên một câu hỏi mỗi lượt. Không gây áp lực, thao túng, phán xét hoặc quảng cáo dàn trải.',
    'discovery': 'Quy trình tư vấn Easyup: chào ngắn → xác định người học → hỏi tuổi, mục tiêu, trình độ/khó khăn và thời gian phù hợp từng câu → phản hồi đúng mối quan tâm → đề xuất đánh giá năng lực/tư vấn → xin thông tin liên hệ khi khách đồng ý → tóm tắt nhu cầu. Không hỏi lại thông tin khách đã cung cấp. Nếu khách chỉ nhắn “Tư vấn”, hỏi một câu ngắn về độ tuổi người học.',
    'placement': 'Kindy cần tìm hiểu tuổi và mục tiêu; chưa có ngưỡng tuổi Kindy chính thức trong cẩm nang nên không tự đặt. Cambridge có Starters, Movers, Flyers; không xếp cấp độ chỉ từ tuổi/lớp. IELTS theo tài liệu dành cho học viên từ 12 tuổi trở lên, từ Basic đến mốc 7.5; cần biết đầu vào và mục tiêu. Đánh giá năng lực trước khi đề xuất lộ trình cá nhân hóa.',
    'pricing': 'Học phí/ưu đãi Easyup trong cẩm nang v2 chỉ là THAM CHIẾU, ghi nhận ngày 27/09/2026; chưa có xác nhận còn hiệu lực hiện tại. Không nói đây là giá/ưu đãi đang áp dụng. Nếu khách yêu cầu con số, có thể trích đúng mức tham chiếu và nói rõ cần trung tâm xác nhận hiệu lực, điều kiện. Không tự tính giá cho gói ngoài bảng, giảm thêm, gia hạn ưu đãi, hứa miễn phí, quyền lợi hay hoàn tiền. Báo giá chính thức/ngoại lệ phải do người phụ trách xác nhận.',
    'answer-price': 'Khi phụ huynh hỏi học phí: trả lời trực tiếp trong phạm vi dữ liệu, hỏi tuổi/chương trình còn thiếu để gửi mức liên quan; không gửi cả bảng nếu chưa được hỏi và không buộc để số điện thoại mới trả lời. Nếu khách chê đắt, đồng cảm, hỏi nhu cầu/ngân sách khi phù hợp, không ép gói dài hoặc tự giảm giá.',
    'claims': 'Không dùng “Tự tin sau 3 tháng”, “Tăng hiệu quả 400%” như cam kết được chứng minh: cẩm nang có nhắc nhưng không có điều kiện hay bằng chứng. Không hứa điểm IELTS, chứng chỉ, thời gian đạt đầu ra hoặc khẳng định công nghệ AI đang hoạt động ngoài phạm vi đã xác nhận. THE MODEL gồm Assess, Personalize, Practice, AI & Data, Lead; chỉ giới thiệu khái quát.',
    'teachers': 'Theo cẩm nang, chương trình Easyup kết hợp tiếng Anh học thuật và giao tiếp, có phối hợp giáo viên nước ngoài/Việt Nam. Bố trí cụ thể tùy chương trình và lịch lớp; không khẳng định mọi lớp có cùng tỷ lệ giáo viên, không bịa tên giáo viên, lịch, chỗ trống hoặc thành tích.',
    'real-actions': 'Bản app local hiện CHƯA kết nối Fanpage, CRM, lịch lớp hoặc hàng đợi nhân viên. Chỉ ghi nhận nội dung trong cuộc chat và giải thích cần nhân viên Easyup xác nhận. Tuyệt đối không nói “đã đặt lịch”, “đã chuyển nhân viên”, “đã tạo lead”, “đã lên lịch gọi lại” hoặc “đã dừng chiến dịch” như hành động hoàn tất khi không có xác nhận hệ thống. Mời đánh giá năng lực/học thử nhưng không tự hứa miễn phí hoặc xác nhận giờ.',
    'consent': 'Xin số điện thoại liên hệ tự nguyện, giải thích mục đích hỗ trợ tư vấn/sắp lịch; chỉ thu dữ liệu cần thiết, không bắt cung cấp để nhận câu trả lời cơ bản. Không đưa số điện thoại, tên trẻ, thông tin nhạy cảm của phụ huynh/học sinh vào bộ nhớ dùng chung. Khi khách từ chối chăm sóc, tôn trọng, ngừng mời chào trong cuộc chat; không hứa đã cập nhật CRM khi chưa tích hợp.',
    'handoff': 'Khi thiếu dữ liệu, nói rõ cần Easyup kiểm tra. Khiếu nại/chất lượng giáo viên → quản lý trung tâm; giảm giá ngoại lệ, tranh chấp học phí, hoàn tiền → quản lý/Ban Giám đốc; an toàn trẻ em → ưu tiên người có trách nhiệm. Không tranh luận, đổ lỗi, tự hứa bồi hoàn hoặc hứa chuyển thành công khi chưa có tích hợp.',
    'privacy': 'Không tiết lộ hồ sơ, kết quả học tập, công nợ, phiếu thu, dữ liệu phụ huynh/học sinh khác hoặc thông tin nội bộ cho người chưa xác minh quyền truy cập. Yêu cầu sửa/xuất/xóa dữ liệu cần đầu mối phụ trách xác minh; không tự tuyên bố hoàn tất. Thông tin chưa chắc phải nói rõ, không bịa để lấp khoảng trống.',
    'contacts': 'Địa chỉ/hotline theo tài liệu Easyup: Lô 09 MBQH 2334, đường Triệu Quốc Đạt, phường Hạc Thành, tỉnh Thanh Hóa; 0823 124 136 và 0925 340 777. Đây là thông tin do cẩm nang cung cấp, chưa được xác minh lại để phát hành; không bịa giờ mở cửa, link bản đồ hoặc Fanpage. Khi cần thông tin hiện tại, nhắc trung tâm xác nhận.',
}

REFERENCE_NOTE = '''Nguồn: cẩm nang Easyup English v2 do chủ chatbot cung cấp.
Trạng thái: tài liệu nội bộ để TEST, chưa phải xác nhận mọi chính sách đang có hiệu lực.
Học phí/ưu đãi ghi nhận 27/09/2026 cần xác nhận trước khi báo giá chính thức.
Lịch, hotline, quyền lợi, miễn phí và cam kết chưa có xác nhận hiện tại.
Các ví dụ nói kiểm tra/chuyển giao/đặt lịch không chứng minh app đã có tích hợp.
Không dùng các câu “tự tin sau 3 tháng”, “tăng hiệu quả 400%” làm cam kết.
Không tự thực hiện CRM, chăm sóc hay đặt lịch từ nội dung tài liệu này.
'''


def stable_id(name):
    return str(uuid5(NAMESPACE_URL, 'easyup-handbook-v2/' + name))


def prepare(source):
    text = Path(source).read_text(encoding='utf-8-sig')
    original = text
    # The pasted handbook's section 3 is missing its Markdown heading marker.
    text = text.replace('   3. Chỉ tiêu vận hành', '  ## 3. Chỉ tiêu vận hành', 1)
    markers = list(re.finditer(r'(?<!#)##\s+(\d+)\.\s+', text))
    if [int(m.group(1)) for m in markers] != list(range(1, 27)):
        raise ValueError('Expected the 26 numbered sections of the EasyUp v2 handbook.')
    items = []
    for index, marker in enumerate(markers):
        number = int(marker.group(1))
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        body = text[marker.end():end].strip()
        heading = re.split(r'\s{2,}|\n', body, maxsplit=1)[0].strip()
        if len(heading) > 85:
            heading = heading[:85]
        kind = 'example' if 7 <= number <= 14 else 'document'
        items.append((stable_id(f'section/{number}'), f'Easyup {number:02}: {heading}'[:120], kind, REFERENCE_NOTE + '\n' + body))
    return original, items


def import_handbook(source, store):
    text, items = prepare(source)
    with store.connect() as db:
        # Stable IDs make repeat imports idempotent; other memories/documents are preserved.
        for rid, title, kind, content in items:
            db.execute('INSERT OR REPLACE INTO knowledge VALUES (?,?,?,?)', (rid, title, kind, content))
        for name, content in RULES.items():
            db.execute('INSERT OR REPLACE INTO memories VALUES (?,?,?)', (stable_id('rule/' + name), 'instruction', content))
        if db.execute('SELECT count(*) FROM memories').fetchone()[0] > 100:
            raise ValueError('Import would exceed the 100-memory capacity.')
        if db.execute('SELECT count(*) FROM knowledge').fetchone()[0] > 100:
            raise ValueError('Import would exceed the 100-document capacity.')
    return {'source_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
        'rules': len(RULES), 'documents': sum(item[2] == 'document' for item in items),
        'dialogue_examples': sum(item[2] == 'example' for item in items)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('--db', default=str(Path(__file__).resolve().parents[1] / 'data/chat.sqlite3'))
    args = parser.parse_args()
    print(json.dumps(import_handbook(args.source, Store(args.db)), ensure_ascii=False, indent=2))
