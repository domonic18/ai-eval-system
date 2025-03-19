<template>
  <div class="user-avatar" :style="sizeStyle">
    <img
      v-if="avatarSrc"
      :src="avatarSrc"
      :alt="alt"
      class="avatar-img"
      @error="handleError"
    />
    <div v-else class="avatar-fallback" :style="{ fontSize: `${size * 0.4}px` }">
      {{ userInitial }}
    </div>
  </div>
</template>

<script>
import { computed, ref } from 'vue'

export default {
  name: 'UserAvatar',
  
  props: {
    src: {
      type: String,
      default: ''
    },
    alt: {
      type: String,
      default: '用户头像'
    },
    username: {
      type: String,
      default: ''
    },
    size: {
      type: Number,
      default: 40
    }
  },
  
  setup(props) {
    const hasError = ref(false)
    
    // 计算样式
    const sizeStyle = computed(() => ({
      width: `${props.size}px`,
      height: `${props.size}px`
    }))
    
    // 计算头像URL，处理错误情况
    const avatarSrc = computed(() => {
      if (hasError.value || !props.src) {
        return '/images/default-avatar.png' // 前端静态资源
      }
      return props.src
    })
    
    // 计算用户名首字母（作为备用显示）
    const userInitial = computed(() => {
      if (!props.username) return '?'
      return props.username.charAt(0).toUpperCase()
    })
    
    // 处理图片加载错误
    const handleError = () => {
      hasError.value = true
    }
    
    return {
      sizeStyle,
      avatarSrc,
      userInitial,
      handleError
    }
  }
}
</script>

<style scoped>
.user-avatar {
  border-radius: 50%;
  overflow: hidden;
  display: inline-flex;
  justify-content: center;
  align-items: center;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #e0e0e0;
  color: #555;
  font-weight: bold;
}
</style> 