<!--
@File        : DishPanel.vue
@Author      : taichilei
@Date        : 2025-04-22
@Description : 菜品管理页面，基于 ContentPanel 通用组件
-->
<template>
  <ContentPanel :fetchData="fetchDishList" @update:selected="handleSelected">
    <!-- 搜索区域 -->
    <template #search-form="{ form, onSearch, onReset }">
      <el-form-item label="菜品名称">
        <el-input v-model="form.keyword" clearable placeholder="请输入菜品名称" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="onSearch">搜索</el-button>
        <el-button @click="onReset">重置</el-button>
      </el-form-item>
    </template>

    <!-- 工具栏 -->
    <template #toolbar="{ selected }">
      <el-button type="success" @click="handleAdd">新增菜品</el-button>
      <el-button :disabled="!selected.length" type="danger" @click="handleDelete(selected)"
      >删除
      </el-button>
    </template>

    <!-- 表格列 -->
    <template #columns>
      <el-table-column label="菜品ID" prop="dish_id" width="80" />
      <el-table-column label="菜品名称" prop="name" />
      <el-table-column label="分类" prop="category_name" />
      <el-table-column label="价格" prop="price" />
      <el-table-column label="库存" prop="stock" />
      <el-table-column label="创建时间" prop="created_at" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click="handleEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </template>
  </ContentPanel>

  <el-dialog v-model="dialogVisible" title="新增菜品">
    <el-form :model="form" label-width="80px">
      <el-form-item label="菜名">
        <el-input v-model="form.dishName" />
      </el-form-item>
      <el-form-item label="分类">
        <el-select v-model="form.categoryId" placeholder="请选择">
          <el-option
            v-for="cat in categoryOptions"
            :key="cat.id"
            :label="cat.name"
            :value="cat.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="价格">
        <el-input-number v-model="form.price" :min="0" />
      </el-form-item>
      <el-form-item label="库存">
        <el-input-number v-model="form.stock" :min="0" />
      </el-form-item>
      <el-form-item label="标签">
        <el-select v-model="form.tagNames" filterable multiple placeholder="请选择标签">
          <el-option v-for="tag in allTags" :key="tag.tag_id" :label="tag.name" :value="tag.name" />
        </el-select>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="submitForm">提交</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
  import { onMounted, reactive, ref } from 'vue'
  import { ElMessage, ElMessageBox } from 'element-plus'
  import ContentPanel from '@/components/common/ContentPanel.vue'
  import { createDish, deleteDish, getDishList, updateDish } from '@/api/dish'
  import { getCategoryList } from '@/api/category'
  import { getTagList } from '@/api/tag'

  // console.log('[DishPanel] mounted')

  const dialogVisible = ref(false)
  const form = reactive({
    dishId: null,
    dishName: '',
    categoryId: null,
    price: 0,
    stock: 0,
    tagNames: []
    // imageUrl: '',
  })
  const categoryOptions = ref([])
  const allTags = ref([])

  onMounted(async () => {
    try {
      const res = await getCategoryList({ page: 1, pageSize: 100 })
      const rawData = res?.data
      const list = rawData?.data || rawData?.list || []
      if (!Array.isArray(list)) {
        console.warn('[DishPanel] 分类数据不是数组', list)
      } else {
        categoryOptions.value = list
          .map((cat) => {
            if (!cat.category_id || !cat.name) {
              console.warn('[DishPanel] 分类字段缺失:', cat)
              return null
            }
            return {
              id: cat.category_id,
              name: cat.name
            }
          })
          .filter(Boolean)
      }
      console.log('[DishPanel] 加载分类成功', categoryOptions.value)
    } catch (err) {
      console.error('加载分类失败', err)
    }
    try {
      const res = await getTagList()
      const raw = res.data
      allTags.value = Array.isArray(raw) ? raw : (raw.list || raw.data || [])
    } catch (err) {
      console.error('[DishPanel] 加载标签失败', err)
    }
  })

  const fetchDishList = async (query) => {
    console.log('[DishPanel] fetchDishList query:', query)
    const res = await getDishList(query)
    console.log('[DishPanel] getDishList response:', res)
    // 兼容 mocks 的 data 数组 和 后端返回的 list 字段
    const dataArr = res.data.data || res.data.list || []
    dataArr.sort((a, b) => a.dish_id - b.dish_id)
    dataArr.forEach(item => {
      item._sortKey = item.dish_id
    })
    return {
      list: dataArr,
      total: res.data.total ?? dataArr.length
    }
  }

  const handleAdd = () => {
    resetForm()
    dialogVisible.value = true
  }

  const resetForm = () => {
    form.dishId = null
    form.dishName = ''
    form.categoryId = null
    form.price = 0
    form.stock = 0
    form.tagNames = []
    // form.imageUrl = ''
  }

  const handleEdit = (row) => {
    form.dishId = row.dishId
    form.dishName = row.name
    form.categoryId = row.category_id
    form.price = Number(row.price)
    form.stock = row.stock
    form.tagNames = row.tags || []
    dialogVisible.value = true
  }

  const submitForm = async () => {
    const isEdit = !!form.dishId
    try {
      const payload = {
        name: form.dishName,
        category_id: form.categoryId,
        price: form.price.toFixed(2),
        stock: form.stock,
        tag_names: form.tagNames,
        image_url: '',
        description: '',
        is_available: true
      }
      if (isEdit) {
        await updateDish(form.dishId, payload)
        ElMessage.success('更新成功')
      } else {
        await createDish(payload)
        ElMessage.success('新增成功')
      }
      dialogVisible.value = false
      await fetchDishList({ page: 1 }) // 自动刷新
    } catch (err) {
      console.error(err)
      ElMessage.error(isEdit ? '更新失败' : '新增失败')
    }
  }

  const handleDelete = (selected) => {
    console.log('[DishPanel] handleDelete selected:', selected)
    ElMessageBox.confirm('确定删除选中的菜品？', '警告', { type: 'warning' }).then(async () => {
      for (const item of selected) {
        await deleteDish(item.dishId)
      }
      ElMessage.success('删除成功')
    })
  }

  const handleSelected = (val) => {
    console.log('[DishPanel] selected:', val)
  }
</script>

<style scoped>
  /* 根据需要添加样式 */
</style>
