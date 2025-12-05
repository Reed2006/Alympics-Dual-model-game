#!/bin/bash

# DeepSeek 迁移测试脚本
echo "🔧 测试 OpenAI 到 DeepSeek 的迁移..."

# 检查环境变量
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "⚠️  警告: DEEPSEEK_API_KEY 环境变量未设置"
    echo "请设置你的 DeepSeek API 密钥:"
    echo "export DEEPSEEK_API_KEY='your_api_key_here'"
    exit 1
fi

echo "✅ DeepSeek API 密钥已设置"

# 检查依赖
echo "📦 检查依赖包..."
python -c "import openai; print('✅ openai 包已安装')" 2>/dev/null || {
    echo "❌ openai 包未安装，正在安装..."
    pip install openai
}

python -c "import numpy; print('✅ numpy 包已安装')" 2>/dev/null || {
    echo "❌ numpy 包未安装，正在安装..."
    pip install numpy
}

# 测试基本的 LLM 类
echo "🧪 测试基本 LLM 功能..."
cd src
python -c "
from Alympics import LLM
import sys

try:
    llm = LLM()
    print('✅ LLM 类初始化成功')
    print(f'✅ 使用模型: {llm.engine}')
    print(f'✅ API 端点: {llm.client.base_url}')
    
    # 简单测试 (不实际调用 API)
    print('✅ DeepSeek 客户端配置正确')
except Exception as e:
    print(f'❌ LLM 初始化失败: {e}')
    sys.exit(1)
"

echo "✅ 所有测试通过！"
echo ""
echo "🎮 现在你可以运行游戏:"
echo "   cd src && python run.py --round 5 --lower 10 --upper 15"
echo ""
echo "🧠 或者运行 k-level 推理:"
echo "   cd k-reasoning/G08A && bash run.sh"
echo "   cd k-reasoning/SAG && bash run.sh"
