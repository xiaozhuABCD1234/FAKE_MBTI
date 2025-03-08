const { createApp } = Vue;

createApp({
    data() {
        return {
            chineseTitle: "中文",
            englishTitle: "RGLX",
            file: null,
            numPoints: 5000,
            detailLevel: 5,
            originalImage: null,
            processedImage: null,
            isLoading: false,
            error: null,
        };
    },
    methods: {
        onFileChange(e) {
            const file = e.target.files[0];
            if (file) {
                this.file = file;
                this.originalImage = URL.createObjectURL(file);
                this.processedImage = null;
            }
        },
        async submitForm() {
            if (!this.file) {
                this.error = "请先选择图片";
                return;
            }
            this.isLoading = true;
            this.error = null;
            try {
                const formData = new FormData();
                formData.append("file", this.file);
                formData.append("num_points", this.numPoints);
                formData.append("detail_level", this.detailLevel);
                const response = await axios.post("/low_poly_image/", formData, {
                    headers: {
                        "Content-Type": "multipart/form-data",
                    },
                    responseType: "blob",
                });
                const imageUrl = URL.createObjectURL(response.data);
                this.processedImage = imageUrl;
            } catch (err) {
                this.error =
                    "处理失败：" + (err.response?.data?.detail || err.message);
            } finally {
                this.isLoading = false;
            }
        },
    },
}).mount("#app");