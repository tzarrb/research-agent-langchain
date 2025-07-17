import { createRouter, createWebHistory } from 'vue-router'
import ChatView from "@/views/chat/ChatView.vue";
import Chat from "@/views/chat/Chat.vue";
import Home from "@/views/home/Index.vue";
import Login from "@/views/login/Login.vue";
import UploadFile from '@/views/upload/UploadFile.vue';
import Test from "@/views/test/Test.vue";
import TestComponent from "@/views/test/TestComponent.vue";

const routes = [
  {
    path: '/',
    name: 'Chat',
    component: Chat
  },
  {
    path: '/chat',
    name: 'ChatView',
    component: ChatView
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
  },
  {
    path: '/home',
    name: 'Home',
    component: Home,
  },
  {
    path: '/upload',
    name: 'Upload',
    component: UploadFile
  },
  {
    path: '/test',
    name: 'Test',
    component: Test
  },
  {
    path: '/test-comp',
    name: 'TestComponent',
    component: TestComponent
  }
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})


export default router
