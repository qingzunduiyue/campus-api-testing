<template>
  <div>
    <div style="height: 60px; border-bottom: 1px solid #ddd; display: flex; align-items: center;">
      <div style="flex: 1">
        <div style="padding-left: 20px; display: flex; align-items: center">
          <span style="font-size: 30px; color: #1967e3; margin-right: 8px">学</span>
          <div style="font-weight: bold; font-size: 24px; margin-left: 5px">管理系统</div>
        </div>
      </div>
      <div style="width: fit-content; padding-right: 10px; display: flex; align-items: center;">
        <img style="width: 40px; height: 40px; border-radius: 50%" :src="data.user.avatar || '/avatar.svg'" alt="">
        <span style="margin-left: 5px">{{ data.user.name }}</span>
      </div>
    </div>

    <div style="display: flex">
      <div style="width: 200px; border-right: 1px solid #ddd; min-height: calc(100vh - 60px)">
        <el-menu
            router
            style="border: none"
            :default-active="router.currentRoute.value.path"
            :default-openeds="['user']"
        >
          <el-menu-item index="/manager/home">
            <el-icon><HomeFilled /></el-icon>
            <span>系统首页</span>

          </el-menu-item>
          <el-sub-menu index="user">
            <template #title>
              <el-icon><Memo /></el-icon>
              <span>信息管理</span>
            </template>
            <el-menu-item index="/manager/major">
              <el-icon><Tickets /></el-icon>
              <span>专业信息</span>
            </el-menu-item>
            <el-menu-item index="/manager/clazz">
              <el-icon><Tickets /></el-icon>
              <span>班级信息</span>
            </el-menu-item>
          </el-sub-menu>

          <el-sub-menu index="user">
            <template #title>
              <el-icon><Memo /></el-icon>
              <span>用户管理</span>
            </template>
            <el-menu-item index="/manager/admin">
              <el-icon><User /></el-icon>
              <span>管理员信息</span>
            </el-menu-item>
          </el-sub-menu>
          <el-menu-item index="/manager/person">
            <el-icon><User /></el-icon>
            <span>个人资料</span>
          </el-menu-item>
          <el-menu-item index="/manager/password">
            <el-icon><Lock /></el-icon>
            <span>修改密码</span>
          </el-menu-item>
          <el-menu-item index="/login" @click="logout">
            <el-icon><SwitchButton /></el-icon>
            <span>退出系统</span>
          </el-menu-item>
        </el-menu>
      </div>

      <div style="flex: 1; width: 0; background-color: #f8f8ff; padding: 10px">
        <router-view @updateUser="updateUser" />
      </div>
    </div>

  </div>
</template>

<script setup>
import { reactive } from "vue";
import router from "@/router";
import {ElMessage} from "element-plus";

const data = reactive({
  user: JSON.parse(localStorage.getItem('system-user') || '{}')
})

if (!data.user?.id) {
  ElMessage.error('请登录！')
  router.push('/login')
}

const updateUser = () => {
  data.user = JSON.parse(localStorage.getItem('system-user') || '{}')
}

const logout = () => {
  ElMessage.success('退出成功')
  localStorage.removeItem('system-user')
  router.push('/login')
}
</script>

<style scoped>

:deep(th)  {
  color: #333;
}
</style>