import { useState, useEffect, useRef } from 'react'
import './App.css'

function App() {
  const [speed, setSpeed] = useState(5)
  const [isGenerating, setIsGenerating] = useState(false)
  const [generatedText, setGeneratedText] = useState('')
  const [tokens, setTokens] = useState(0)
  const [time, setTime] = useState(0)
  const [actualSpeed, setActualSpeed] = useState(0)
  const [language, setLanguage] = useState('zh')

  const textRef = useRef(null)
  const animationRef = useRef(null)
  const startTimeRef = useRef(null)

  const fullText = `在那遥远的维罗纳城邦，两个同样尊贵的家族，
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
那永恒的爱情如何战胜了一切。`

  // 简单估算每个字符约为1个token
  const tokenize = (text) => {
    return text.length
  }

  const startGeneration = () => {
    if (isGenerating) return

    setIsGenerating(true)
    setGeneratedText('')
    setTokens(0)
    setTime(0)
    startTimeRef.current = Date.now()

    // 计算每个token生成的时间间隔（毫秒）
    const interval = 1000 / speed
    let currentIndex = 0

    const generate = () => {
      if (currentIndex < fullText.length) {
        // 添加下一个字符
        const nextChar = fullText[currentIndex]
        setGeneratedText(prev => prev + nextChar)
        currentIndex++

        // 更新tokens计数和时间
        const currentTokens = tokenize(fullText.slice(0, currentIndex))
        setTokens(currentTokens)

        const currentTime = (Date.now() - startTimeRef.current) / 1000
        setTime(currentTime.toFixed(2))

        // 计算实际速度
        if (currentTime > 0) {
          setActualSpeed((currentTokens / currentTime).toFixed(2))
        }

        // 继续生成
        animationRef.current = setTimeout(generate, interval)
      } else {
        // 生成完成
        setIsGenerating(false)
      }
    }

    // 开始生成
    animationRef.current = setTimeout(generate, interval)
  }

  // 清理定时器
  useEffect(() => {
    return () => {
      if (animationRef.current) {
        clearTimeout(animationRef.current)
      }
    }
  }, [])

  // 当文本更新时，滚动到底部
  useEffect(() => {
    if (textRef.current) {
      textRef.current.scrollTop = textRef.current.scrollHeight
    }
  }, [generatedText])

  // 语言文本
  const texts = {
    zh: {
      title: 'Token 生成速度可视化',
      subtitle: '实时体验不同的 token 生成速度',
      speedLabel: '生成速度',
      rangeLabel: '范围',
      slow: '慢',
      medium: '中等',
      fast: '快',
      startButton: '开始生成'
    },
    en: {
      title: 'Token Generation Speed Visualizer',
      subtitle: 'Experience different token generation speeds in real-time',
      speedLabel: 'Generation Speed',
      rangeLabel: 'Range',
      slow: 'Slow',
      medium: 'Medium',
      fast: 'Fast',
      startButton: 'Start Generation'
    }
  }

  // 获取当前语言的文本
  const t = texts[language]

  return (
    <div className="container">
      <div className="language-toggle">
        <select
          className="lang-select"
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
        >
          <option value="zh">中文</option>
          <option value="en">English</option>
        </select>
      </div>

      <div className="header">
        <h1>{t.title}</h1>
        <p className="subtitle">{t.subtitle}</p>
      </div>

      <div className="speed-control">
        <div className="speed-label">
          <span>{t.speedLabel}: {speed} tokens/s</span>
          <span className="range-label">{t.rangeLabel}: 1-100 tokens/s</span>
        </div>
        <div className="slider-container">
          <input
            type="range"
            min="1"
            max="100"
            value={speed}
            onChange={(e) => setSpeed(parseInt(e.target.value))}
            disabled={isGenerating}
            className="slider"
          />
          <div className="slider-labels">
            <span>1</span>
            <span>25</span>
            <span>50</span>
            <span>75</span>
            <span>100</span>
          </div>
          <div className="slider-descriptions">
            <span>{t.slow}</span>
            <span>{t.medium}</span>
            <span>{t.fast}</span>
          </div>
        </div>
      </div>

      <div className="stats">
        <div className="stat-item">
          <span>Tokens: {tokens}</span>
        </div>
        <div className="stat-item">
          <span>Time: {time}s</span>
        </div>
        <div className="stat-item">
          <span>Speed: {actualSpeed} tokens/s</span>
        </div>
      </div>

      <div className="text-output" ref={textRef}>
        {generatedText || <span className="placeholder"></span>}
      </div>

      <button
        className="generate-button"
        onClick={startGeneration}
        disabled={isGenerating}
      >
        {t.startButton}
      </button>
    </div>
  )
}

export default App
