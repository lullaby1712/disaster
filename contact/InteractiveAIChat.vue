<template>
  <div class="ai-chat-panel">
    <h3>与AI分析师对话</h3>
    <div class="chat-messages" ref="chatMessagesContainer">
      <div v-for="(msg, idx) in messages" :key="idx" class="chat-msg" :class="[msg.sender]">
        <span class="sender-label">{{ msg.sender === 'ai' ? 'AI分析师' : '您' }}:</span>
        <span class="msg-text" v-html="msg.text"></span>
      </div>
      <div v-if="isTyping" class="chat-msg ai">
        <span class="sender-label">AI分析师:</span>
        <span class="typing-indicator">...</span>
      </div>
    </div>
    <div class="chat-input-area">
      <input
        v-model="userInput"
        @keyup.enter="sendMessage"
        placeholder="在此输入您的问题..."
        :disabled="isTyping"
      />
      <button @click="sendMessage" :disabled="!userInput.trim() || isTyping">发送</button>
      <button @click="checkHealth" class="health-btn" :disabled="isCheckingHealth">
        {{ isCheckingHealth ? '检查中...' : '系统状态' }}
      </button>
    </div>
    <div class="ai-disclaimer">
      AI生成的内容仅供参考，请结合实际情况进行决策。
    </div>
  </div>
</template>

<script>
export default {
  name: 'InteractiveAIChat',
  props: {
    selectedSubModel: Object,
    selectedRegion: String,
    drivingDatasets: Array,
  },
  data() {
    return {
      userInput: '',
      isTyping: false,
      isCheckingHealth: false,
      messages: [
        { sender: 'ai', text: '您好！我是智枢AI分析师。您可以向我提问关于当前灾害情况、数据源或模型分析的任何问题。' }
      ],
    };
  },
  methods: {
    // 滚动条自动滚动到底部
    scrollToBottom() {
      this.$nextTick(() => {
        const container = this.$refs.chatMessagesContainer;
        if (container) {
          container.scrollTop = container.scrollHeight;
        }
      });
    },
    async sendMessage() {
      const userMessage = this.userInput.trim();
      if (!userMessage || this.isTyping) return;

      this.messages.push({ sender: 'user', text: userMessage });
      this.userInput = '';
      this.isTyping = true;
      this.scrollToBottom();

      
      try {
        // 准备发送到后端的数据
        const requestPayload = {
          question: userMessage,
          context: {
            region: this.selectedRegion,
            model: this.selectedSubModel,
            datasets: this.drivingDatasets.map(d => ({ name: d.name, source: d.source })),
          }
        };

        // 调用后端 /api/chat 接口
        const response = await fetch('/api/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(requestPayload),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.message || '与AI服务通信失败');
        }

        const data = await response.json();
        // 将从后端获取的真实回复添加到消息列表
        this.messages.push({ sender: 'ai', text: data.reply });

      } catch (error) {
        console.error('AI Chat Error:', error);
        // 出错提示
        this.messages.push({ sender: 'ai', text: `抱歉，我遇到了一些麻烦，暂时无法回答。错误信息: ${error.message}` });
      } finally {
        this.isTyping = false;
        this.scrollToBottom();
      }
    },

    async checkHealth() {
      this.isCheckingHealth = true;
      
      try {
        const response = await fetch('/api/langgraph/health', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          }
        });

        const data = await response.json();
        
        if (data.success) {
          this.messages.push({ 
            sender: 'ai', 
            text: `**系统状态检查结果:**\n✅ LangGraph应急管理系统运行正常\n\n**详细信息:**\n${JSON.stringify(data.langgraph_status, null, 2)}` 
          });
        } else {
          this.messages.push({ 
            sender: 'ai', 
            text: `**系统状态检查结果:**\n❌ LangGraph应急管理系统连接失败\n\n**错误信息:** ${data.message}` 
          });
        }
      } catch (error) {
        console.error('Health Check Error:', error);
        this.messages.push({ 
          sender: 'ai', 
          text: `**系统状态检查结果:**\n❌ 无法连接到LangGraph应急管理系统\n\n**错误信息:** ${error.message}` 
        });
      } finally {
        this.isCheckingHealth = false;
        this.scrollToBottom();
      }
    },
    
  },
};
</script>

<style scoped>
/* 样式保持不变 */
.ai-chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #f8f9fa;
  border: 1px solid #e0e6ed;
  border-radius: 8px;
  padding: 16px;
}
h3 {
  margin: 0 0 16px 0;
  color: #2C7BE5;
  border-bottom: 1px solid #e0e6ed;
  padding-bottom: 8px;
}
.chat-messages {
  flex-grow: 1;
  overflow-y: auto;
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.chat-msg {
  padding: 8px 12px;
  border-radius: 6px;
  max-width: 85%;
  line-height: 1.5;
  word-wrap: break-word;
}
.chat-msg.user {
  background-color: #2C7BE5;
  color: white;
  align-self: flex-end;
}
.chat-msg.ai {
  background-color: #fff;
  border: 1px solid #e0e6ed;
  align-self: flex-start;
}
.sender-label {
  font-weight: bold;
  margin-right: 6px;
}
.msg-text {
  /* 允许内容换行 */
  white-space: pre-wrap; 
}
.typing-indicator {
    display: inline-block;
    animation: typing 1s infinite;
}
@keyframes typing {
    0% { content: "."; }
    33% { content: ".."; }
    66% { content: "..."; }
}
.chat-input-area {
  display: flex;
  gap: 8px;
}
.chat-input-area input {
  flex-grow: 1;
  border: 1px solid #ced4da;
  border-radius: 4px;
  padding: 8px 12px;
  font-size: 14px;
}
.chat-input-area button {
  background-color: #2C7BE5;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 8px 16px;
  cursor: pointer;
  transition: background-color .2s;
}
.chat-input-area button:hover {
  background-color: #185fa3;
}
.chat-input-area button:disabled {
  background-color: #a0b3d1;
  cursor: not-allowed;
}
.health-btn {
  background-color: #28a745 !important;
  margin-left: 8px;
}
.health-btn:hover {
  background-color: #218838 !important;
}
.health-btn:disabled {
  background-color: #6c757d !important;
}
.ai-disclaimer {
  font-size: 11px;
  color: #888;
  margin-top: 12px;
  text-align: center;
}
</style>