const SAMPLE_TEXT = `在那遥远的维罗纳城邦，两个同样尊贵的家族，
因宿怨长存而再起纷争，血染古城墙。
命运的双星从这对世仇诞生，
一对恋人以死亡终结了父辈的仇恨。
他们悲剧性的爱情与父母的愤怒，
唯有他们的死亡才能平息这场争端，
这便是我们今日为您呈现的故事，
请静心聆听，我们将在这舞台上重现。
在这古老的街道上，荣誉与剑相伴，
年轻的心灵在命运的指引下相遇。
当朱丽叶的眼眸遇见罗密欧的凝视，
世间再无比这更纯粹的爱情。
然而命运弄人，他们的相爱注定坎坷，
家族的仇恨如高墙般将他们阻隔。
但爱情啊，它超越了所有的界限，
即使是死亡也无法将其消散。
请听这悲伤的故事，关于爱与恨，
关于生与死，关于和解与遗憾。
在这两个小时的旅程中，我们将展示，
那永恒的爱情如何战胜了一切。`;

const COPY = {
  zh: {
    title: 'Token 生成速度可视化',
    output: '生成输出',
    outputMeta: '固定文本样本，按设定速度逐字渲染',
    placeholder: '点击开始后显示生成内容',
    speed: '生成速度',
    start: '开始',
    stop: '停止',
    reset: '重置',
    tokens: 'Tokens',
    elapsed: '耗时',
    actual: '实际速度',
  },
  en: {
    title: 'Token Generation Speed Visualizer',
    output: 'Generated Output',
    outputMeta: 'A fixed sample rendered character by character',
    placeholder: 'Start to render the sample text',
    speed: 'Generation Speed',
    start: 'Start',
    stop: 'Stop',
    reset: 'Reset',
    tokens: 'Tokens',
    elapsed: 'Elapsed',
    actual: 'Actual Speed',
  },
};

function tokenVisualizer() {
  return {
    language: 'zh',
    languageMenuOpen: false,
    speed: 24,
    isRunning: false,
    generatedText: '',
    tokenCount: 0,
    elapsedSeconds: 0,
    actualSpeed: 0,
    animationId: null,
    startTime: 0,
    fullText: SAMPLE_TEXT,

    get t() {
      return COPY[this.language];
    },

    get progressPercent() {
      if (!this.fullText.length) {
        return 0;
      }
      return Math.min(100, (this.tokenCount / this.fullText.length) * 100);
    },

    setLanguage(language) {
      this.language = language;
      this.languageMenuOpen = false;
    },

    start() {
      if (this.isRunning) {
        return;
      }

      this.cancelFrame();
      this.generatedText = '';
      this.tokenCount = 0;
      this.elapsedSeconds = 0;
      this.actualSpeed = 0;
      this.startTime = performance.now();
      this.isRunning = true;
      this.tick();
    },

    reset() {
      this.cancelFrame();
      this.isRunning = false;
      this.generatedText = '';
      this.tokenCount = 0;
      this.elapsedSeconds = 0;
      this.actualSpeed = 0;
    },

    tick() {
      if (!this.isRunning) {
        return;
      }

      const elapsedMs = performance.now() - this.startTime;
      const nextCount = Math.min(this.fullText.length, Math.floor((elapsedMs / 1000) * this.speed));

      if (nextCount !== this.tokenCount) {
        this.tokenCount = nextCount;
        this.generatedText = this.fullText.slice(0, nextCount);
        this.elapsedSeconds = elapsedMs / 1000;
        this.actualSpeed = this.elapsedSeconds > 0 ? this.tokenCount / this.elapsedSeconds : 0;
        this.$nextTick(() => this.scrollOutput());
      } else {
        this.elapsedSeconds = elapsedMs / 1000;
      }

      if (this.tokenCount >= this.fullText.length) {
        this.isRunning = false;
        this.cancelFrame();
        return;
      }

      this.animationId = requestAnimationFrame(() => this.tick());
    },

    scrollOutput() {
      if (this.$refs.output) {
        this.$refs.output.scrollTop = this.$refs.output.scrollHeight;
      }
    },

    cancelFrame() {
      if (this.animationId !== null) {
        cancelAnimationFrame(this.animationId);
        this.animationId = null;
      }
    },
  };
}
