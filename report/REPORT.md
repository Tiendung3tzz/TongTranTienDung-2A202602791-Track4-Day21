# Báo cáo Day 6: Độ nhạy của pipeline phát hiện vật cản

> CP1: claim nháp; kết luận sẽ được cập nhật bằng số liệu chạy thật.

- **Họ tên:** Tống Trần Tiến Dũng
- **MSSV:** 2A202602791
- **Lớp:** AI20K-T4
- **Link repo:** https://github.com/Tiendung3tzz/TongTranTienDung-02791-Track4-Day21
- **Topic:** D — Robot/drone obstacle
- **Dataset:** data/kitti_mini (chính), data/synthetic và data/nuscenes_mini_subset (kiểm tra projection)
- **Các frame đã dùng:** KITTI 000008, 000011, 000049; synthetic 000000; nuScenes scene-0103_010

> Hãy viết ngắn: mỗi mục từ 3 đến 8 dòng, ưu tiên số liệu và hình ảnh.

## 1. Claim

Một câu khẳng định kỹ thuật có thể kiểm chứng. Ví dụ: *"Lệch yaw 1° làm 12% điểm LiDAR rơi ra khỏi vật thể ở 30 m, phát hiện được bằng edge-alignment score với ngưỡng X."*

Claim nháp: Tăng DBSCAN eps từ 0.3 m lên 0.8 m, giữ voxel 0.15 m, ngưỡng RANSAC 0.1 m và min_points 10, làm số cụm giảm ít nhất 20% trên ít nhất 2/3 frame KITTI 000008, 000011, 000049. Nếu số liệu bác bỏ giả thuyết, sẽ ghi rõ kết luận thực tế.

## 2. Evidence

Bảng hoặc plot số liệu, kèm ảnh/video demo. Ghi rõ đường dẫn file trong `results/`.

| Cấu hình / mức perturb | Metric 1 | Metric 2 | Ghi chú |
|---|---|---|---|
| [ĐIỀN] | | | |

![demo](../results/figures/[ĐIỀN].png)

## 3. Failure case

Nêu khi nào hệ thống hoặc phương pháp fail, vì sao fail, và liên hệ tới lớp nào trong 6 lớp debug: I/O, Geometry, Time, Preprocess, Model, Metric.

![failure](../results/figures/fail_[ĐIỀN].png)

[ĐIỀN]

## 4. Khuyến nghị nếu triển khai thật

Use-case cụ thể (ADAS / robot / drone), trade-off và bước tiếp theo.

[ĐIỀN]

## 5. Cách chạy lại

Các lệnh tái tạo lại toàn bộ kết quả từ repo sạch.

```bash
[ĐIỀN]
```

## 6. Khai báo sử dụng AI

Ghi rõ đã dùng công cụ AI nào, dùng vào việc gì, và bạn đã tự kiểm chứng kết quả đó bằng cách nào. Nếu không dùng AI, ghi "Không sử dụng". Xem quy định ở `RULES.md` mục 2.

| Công cụ | Dùng cho việc gì | Bạn đã kiểm chứng thế nào |
|---|---|---|
| [ĐIỀN] | | |
