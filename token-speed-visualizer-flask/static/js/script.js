document.addEventListener('DOMContentLoaded', function() {
    // DOM 元素
    const speedSlider = document.getElementById('speedSlider');
    const speedValue = document.getElementById('speedValue');
    const generateButton = document.getElementById('generateButton');
    const textOutput = document.getElementById('textOutput');
    const tokenCount = document.getElementById('tokenCount');
    const timeElapsed = document.getElementById('timeElapsed');
    const actualSpeed = document.getElementById('actualSpeed');
    const langButton = document.getElementById('langButton');
    const langDropdown = document.getElementById('langDropdown');

    // 状态变量
    let isGenerating = false;
    let currentIndex = 0;
    let startTime = null;
    let animationId = null;
    let currentLanguage = 'zh';

    // 初始化
    speedValue.textContent = speedSlider.value;

    // 加载翻译
    loadTranslations(currentLanguage);

    // 事件监听器
    speedSlider.addEventListener('input', function() {
        speedValue.textContent = this.value;
    });

    generateButton.addEventListener('click', function() {
        if (isGenerating) return;
        startGeneration();
    });

    // 语言切换
    langButton.addEventListener('click', function(e) {
        e.stopPropagation();
        langDropdown.classList.toggle('hidden');
    });

    // 点击外部关闭下拉菜单
    document.addEventListener('click', function(e) {
        if (!langDropdown.contains(e.target) && e.target !== langButton) {
            langDropdown.classList.add('hidden');
        }
    });

    // 语言选项点击
    document.querySelectorAll('.lang-option').forEach(option => {
        option.addEventListener('click', function() {
            const lang = this.getAttribute('data-lang');
            currentLanguage = lang;

            // 更新按钮文本
            langButton.textContent = lang === 'zh' ? '中文' : 'English';

            // 更新活动状态
            document.querySelectorAll('.lang-option').forEach(opt => {
                opt.classList.remove('active');
            });
            this.classList.add('active');

            // 加载翻译
            loadTranslations(lang);

            // 关闭下拉菜单
            langDropdown.classList.add('hidden');
        });
    });

    // 函数定义
    function startGeneration() {
        // 重置状态
        isGenerating = true;
        currentIndex = 0;
        textOutput.textContent = '';
        tokenCount.textContent = '0';
        timeElapsed.textContent = '0';
        actualSpeed.textContent = '0.00';
        startTime = Date.now();

        // 禁用滑块和按钮
        speedSlider.disabled = true;
        generateButton.disabled = true;

        // 开始生成
        generateText();
    }

    // 简化实现，使用更可靠的方法
    // 预加载文本，减少网络延迟影响
    let textCache = '';
    let lastFetchTime = 0;
    const FETCH_CHUNK_SIZE = 50; // 每次获取50个字符

    // 预加载文本
    function preloadText() {
        if (textCache.length > 100) return; // 如果缓存中已有足够的文本，则不需要预加载

        const now = Date.now();
        if (now - lastFetchTime < 100) return; // 限制请求频率

        lastFetchTime = now;
        const fetchIndex = currentIndex + textCache.length;

        fetch(`/api/text_chunk?index=${fetchIndex}&chunk_size=${FETCH_CHUNK_SIZE}`)
            .then(response => response.json())
            .then(data => {
                if (!data.done) {
                    textCache += data.text;
                }
            })
            .catch(error => {
                console.error('Error preloading text:', error);
            });
    }

    function generateText() {
        if (!isGenerating) return;

        // 如果缓存为空且没有预加载中，则开始预加载
        if (textCache.length === 0) {
            preloadText();
            // 等待预加载完成后再继续
            setTimeout(generateText, 50);
            return;
        }

        const speed = parseInt(speedSlider.value);
        const targetInterval = 1000 / speed; // 目标间隔（毫秒）

        // 获取当前时间
        const now = Date.now();
        const elapsedSinceStart = now - startTime;

        // 计算理论上应该生成的字符数（基于设定速度和已经过的时间）
        const theoreticalCount = Math.floor(speed * elapsedSinceStart / 1000);

        // 如果实际生成的字符数落后于理论值，则追赶
        if (currentIndex < theoreticalCount && textCache.length > 0) {
            // 计算需要追赶的字符数，但限制一次最多追赶10个字符
            const catchUpCount = Math.min(theoreticalCount - currentIndex, 10, textCache.length);

            // 从缓存中获取字符
            const textToAdd = textCache.substring(0, catchUpCount);
            textCache = textCache.substring(catchUpCount);

            // 添加字符到输出
            textOutput.textContent += textToAdd;

            // 滚动到底部
            textOutput.scrollTop = textOutput.scrollHeight;

            // 更新计数
            currentIndex += catchUpCount;
            tokenCount.textContent = currentIndex;

            // 如果缓存不足，预加载更多文本
            if (textCache.length < 50) {
                preloadText();
            }
        } else if (textCache.length > 0) {
            // 正常速度下的生成
            // 从缓存中获取一个字符
            const textToAdd = textCache.charAt(0);
            textCache = textCache.substring(1);

            // 添加字符到输出
            textOutput.textContent += textToAdd;

            // 滚动到底部
            textOutput.scrollTop = textOutput.scrollHeight;

            // 更新计数
            currentIndex++;
            tokenCount.textContent = currentIndex;

            // 如果缓存不足，预加载更多文本
            if (textCache.length < 50) {
                preloadText();
            }
        }

        // 更新时间和速度显示
        const currentTime = elapsedSinceStart / 1000;
        timeElapsed.textContent = currentTime.toFixed(2);

        // 计算实际速度
        if (currentTime > 0) {
            actualSpeed.textContent = (currentIndex / currentTime).toFixed(2);
        }

        // 检查是否生成完成
        if (textCache.length === 0 && currentIndex > 0 && !preloadText()) {
            // 再次检查是否真的完成了
            fetch(`/api/text?index=${currentIndex}`)
                .then(response => response.json())
                .then(data => {
                    if (data.done) {
                        finishGeneration();
                    } else {
                        // 还没完成，继续生成
                        textCache += data.text;
                        animationId = requestAnimationFrame(generateText);
                    }
                })
                .catch(error => {
                    console.error('Error checking completion:', error);
                    finishGeneration();
                });
        } else {
            // 计算下一次生成的时间
            const nextRenderTime = Math.max(1, targetInterval - (Date.now() - now));
            animationId = setTimeout(generateText, nextRenderTime);
        }
    }

    function finishGeneration() {
        isGenerating = false;
        speedSlider.disabled = false;
        generateButton.disabled = false;

        // 清理缓存和计时器
        textCache = '';
        lastFetchTime = 0;

        if (animationId) {
            if (typeof animationId === 'number') {
                clearTimeout(animationId);
            } else {
                cancelAnimationFrame(animationId);
            }
            animationId = null;
        }
    }

    function loadTranslations(lang) {
        fetch(`/api/translations?lang=${lang}`)
            .then(response => response.json())
            .then(translations => {
                // 更新UI文本
                document.getElementById('title').textContent = translations.title;
                document.getElementById('subtitle').textContent = translations.subtitle;
                document.getElementById('speedLabel').textContent = translations.speedLabel;
                document.getElementById('rangeLabel').textContent = translations.rangeLabel;
                document.getElementById('slow').textContent = translations.slow;
                document.getElementById('medium').textContent = translations.medium;
                document.getElementById('fast').textContent = translations.fast;
                generateButton.textContent = translations.startButton;
            })
            .catch(error => {
                console.error('Error loading translations:', error);
            });
    }
});
