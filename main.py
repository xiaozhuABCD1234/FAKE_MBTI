import cv2
import numpy as np
import concurrent.futures

def get_low_poly_image(image, num_points=1000, detail_level=5):
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
    low_thresh = otsu_thresh * 0.5
    high_thresh = otsu_thresh * 1.5
    edges = cv2.Canny(blurred, low_thresh, high_thresh)

    # 特征点采集优化
    ys, xs = np.where(edges > 0)
    edge_points = np.column_stack((xs, ys))
    
    # 智能点采样策略
    if len(edge_points) > num_points * 0.8:
        # 保持至少20%的随机点
        edge_sample = int(num_points * 0.8)
        indices = np.random.choice(len(edge_points), edge_sample, replace=False)
        points = edge_points[indices]
        num_random = num_points - edge_sample
    else:
        points = edge_points
        num_random = num_points - len(points)

    # 高效生成随机点
    if num_random > 0:
        random_x = np.random.randint(0, w, size=num_random)
        random_y = np.random.randint(0, h, size=num_random)
        random_points = np.column_stack((random_x, random_y))
        points = np.vstack((points, random_points)) if len(points) > 0 else random_points

    # Delaunay三角剖分
    rect = (0, 0, w, h)
    subdiv = cv2.Subdiv2D(rect)
    subdiv.insert(points.astype(np.float32))  # 直接使用numpy数组

    # 获取三角形并过滤无效三角形
    triangle_list = []
    for t in subdiv.getTriangleList():
        # 过滤超出边界的顶点
        if all(0 <= t[i] <= w and 0 <= t[i+1] <= h for i in range(0, 6, 2)):
            triangle_list.append(t)
    triangle_list = np.array(triangle_list)

    # 创建结果画布
    result_img = np.full_like(image, 255)  # 白色背景

    # 多线程处理三角形绘制
    def draw_triangle(t):
        pt1 = (int(t[0]), int(t[1]))
        pt2 = (int(t[2]), int(t[3]))
        pt3 = (int(t[4]), int(t[5]))
        
        # 计算颜色采样区域
        min_x = max(0, int(min(t[0], t[2], t[4])))
        max_x = min(w-1, int(max(t[0], t[2], t[4])))
        min_y = max(0, int(min(t[1], t[3], t[5])))
        max_y = min(h-1, int(max(t[1], t[3], t[5])))
        
        # 采样区域平均颜色
        roi = image[min_y:max_y+1, min_x:max_x+1]
        if roi.size == 0:
            return
        color = np.mean(roi, axis=(0, 1)).astype(int).tolist()
        
        # 绘制抗锯齿三角形
        cv2.fillConvexPoly(result_img, np.array([pt1, pt2, pt3]), color, cv2.LINE_AA)

    # 使用线程池并行处理
    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(draw_triangle, triangle_list)

    return result_img

# 使用示例
if __name__ == "__main__":
    image = cv2.imread("./image-1.png")
    
    if image is None:
        print("图像加载失败，请检查路径")
    else:
        result = get_low_poly_image(image, num_points=2500, detail_level=5)
        cv2.imshow("Optimized Low Poly Art", result)
        cv2.imwrite("optimized_output.jpg", result, [cv2.IMWRITE_JPEG_QUALITY, 90])
        cv2.waitKey(0)
        cv2.destroyAllWindows()