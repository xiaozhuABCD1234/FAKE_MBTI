import cv2
import numpy as np
import concurrent.futures


def get_low_poly_image(
    image: np.ndarray, num_points: int = 1000, detail_level: int = 5
) -> np.ndarray:
    # 参数校验
    detail_level = max(1, min(detail_level, 5))
    num_points = max(100, num_points)

    # 图像预处理
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 动态计算模糊参数
    blur_size = 5 + 2 * detail_level
    blur_size = blur_size + 1 if blur_size % 2 == 0 else blur_size
    blurred = cv2.GaussianBlur(gray, (blur_size, blur_size), 0)

    # 自适应阈值计算
    otsu_thresh, _ = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    edges = cv2.Canny(blurred, otsu_thresh * 0.5, otsu_thresh * 1.5)

    # 特征点采集优化
    ys, xs = np.where(edges > 0)
    edge_points = np.column_stack((xs, ys))

    # 智能点采样策略
    if len(edge_points) > num_points * 0.8:
        edge_sample = int(num_points * 0.8)
        indices = np.random.choice(len(edge_points), edge_sample, replace=False)
        points = edge_points[indices]
        num_random = num_points - edge_sample
    else:
        points = edge_points
        num_random = num_points - len(points)

    # 高效生成随机点
    if num_random > 0:
        random_points = np.random.randint([0, 0], [w, h], (num_random, 2))
        points = (
            np.vstack([points, random_points]) if len(points) > 0 else random_points
        )

    # Delaunay三角剖分
    rect = (0, 0, w, h)
    subdiv = cv2.Subdiv2D(rect)
    subdiv.insert(points.astype(np.float32))

    # 过滤无效三角形
    triangle_list = []
    for t in subdiv.getTriangleList():
        if all(0 <= t[i] < w and 0 <= t[i + 1] < h for i in range(0, 6, 2)):
            triangle_list.append(t)

    # 预处理积分图
    integral_b = cv2.integral(image[:, :, 0], sdepth=cv2.CV_64F)
    integral_g = cv2.integral(image[:, :, 1], sdepth=cv2.CV_64F)
    integral_r = cv2.integral(image[:, :, 2], sdepth=cv2.CV_64F)

    # 多线程颜色计算
    triangles_with_colors = []

    def process_triangle(t):
        # 解析三角形顶点
        pts = [(int(t[i]), int(t[i + 1])) for i in range(0, 6, 2)]

        # 计算包围盒
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        min_x, max_x = max(0, min(xs)), min(w - 1, max(xs))
        min_y, max_y = max(0, min(ys)), min(h - 1, max(ys))

        if min_x >= max_x or min_y >= max_y:
            return None

        # 使用积分图计算平均颜色
        try:
            sum_b = (
                integral_r[max_y + 1, max_x + 1]
                - integral_r[max_y + 1, min_x]
                - integral_r[min_y, max_x + 1]
                + integral_r[min_y, min_x]
            )
            sum_g = (
                integral_g[max_y + 1, max_x + 1]
                - integral_g[max_y + 1, min_x]
                - integral_g[min_y, max_x + 1]
                + integral_g[min_y, min_x]
            )
            sum_r = (
                integral_b[max_y + 1, max_x + 1]
                - integral_b[max_y + 1, min_x]
                - integral_b[min_y, max_x + 1]
                + integral_b[min_y, min_x]
            )
        except:
            return None

        area = (max_x - min_x + 1) * (max_y - min_y + 1)
        if area == 0:
            return None

        color = (int(sum_r / area), int(sum_g / area), int(sum_b / area))
        return (pts, color)

    # 并行处理三角形
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_triangle, t) for t in triangle_list]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                triangles_with_colors.append(result)

    # 创建结果图像
    result_img = np.full_like(image, 255)

    # 单线程绘制保证线程安全
    for pts, color in triangles_with_colors:
        cv2.fillConvexPoly(result_img, np.array(pts), color, lineType=cv2.LINE_AA)

    return result_img
