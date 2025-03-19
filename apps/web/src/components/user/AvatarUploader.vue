<template>
  <div class="avatar-uploader">
    <div class="avatar-preview">
      <img :src="avatarUrl" alt="用户头像" class="avatar-image" />
      <div class="avatar-overlay" @click="triggerFileInput">
        <i class="el-icon-camera"></i>
        <span>更换头像</span>
      </div>
    </div>
    <input
      type="file"
      ref="fileInput"
      accept="image/*"
      class="file-input"
      @change="handleFileChange"
    />
  </div>
</template>

<script>
import { ref, computed, getCurrentInstance } from 'vue'
import { useStore } from 'vuex'
import { ElMessage } from 'element-plus'

export default {
  name: 'AvatarUploader',
  
  setup() {
    const store = useStore()
    const fileInput = ref(null)
    const { proxy } = getCurrentInstance()
    
    // 计算属性 - 当前头像URL，使用默认头像作为备用
    const avatarUrl = computed(() => {
      const user = store.state.auth.user
      return user?.avatar || '/images/default-avatar.png'
    })
    
    // 触发文件选择
    const triggerFileInput = () => {
      fileInput.value.click()
    }
    
    // 处理文件选择
    const handleFileChange = async (event) => {
      const file = event.target.files?.[0]
      if (!file) return
      
      // 验证文件类型
      if (!file.type.startsWith('image/')) {
        ElMessage.error('请选择图片文件')
        return
      }
      
      // 验证文件大小 (限制为2MB)
      if (file.size > 2 * 1024 * 1024) {
        ElMessage.error('图片大小不能超过2MB')
        return
      }
      
      // 上传头像
      try {
        const formData = new FormData()
        formData.append('file', file)
        
        await proxy.$http.post('/api/v1/users/avatar', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        })
        
        // 刷新用户信息
        await store.dispatch('auth/getCurrentUser')
        ElMessage.success('头像更新成功')
      } catch (error) {
        console.error('上传头像失败:', error)
        ElMessage.error('上传头像失败: ' + (error.response?.data?.detail || '服务器错误'))
      }
      
      // 清空文件输入，允许再次选择同一文件
      event.target.value = ''
    }
    
    return {
      fileInput,
      avatarUrl,
      triggerFileInput,
      handleFileChange
    }
  }
}
</script>

<style scoped>
.avatar-uploader {
  display: inline-block;
}

.avatar-preview {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  overflow: hidden;
  position: relative;
  cursor: pointer;
}

.avatar-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  opacity: 0;
  transition: opacity 0.3s;
  color: white;
}

.avatar-preview:hover .avatar-overlay {
  opacity: 1;
}

.file-input {
  display: none;
}
</style> 