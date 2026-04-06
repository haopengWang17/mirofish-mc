import service from './index'

/**
 * 创建 Monte Carlo 模拟组
 * @param {Object} data - { simulation_id, num_runs, max_concurrency, classification_criteria }
 */
export const createMonteCarloGroup = (data) => {
  return service.post('/api/monte-carlo/create', data)
}

/**
 * 启动 Monte Carlo 模拟组
 * @param {Object} data - { group_id, platform, max_rounds }
 */
export const startMonteCarloGroup = (data) => {
  return service.post('/api/monte-carlo/start', data)
}

/**
 * 获取 Monte Carlo 组状态
 * @param {string} groupId
 */
export const getMonteCarloGroup = (groupId) => {
  return service.get(`/api/monte-carlo/${groupId}`)
}

/**
 * 获取实时进度
 * @param {string} groupId
 */
export const getMonteCarloProgress = (groupId) => {
  return service.get(`/api/monte-carlo/${groupId}/progress`)
}

/**
 * 获取分析结果
 * @param {string} groupId
 */
export const getMonteCarloAnalysis = (groupId) => {
  return service.get(`/api/monte-carlo/${groupId}/analysis`)
}

/**
 * 重新分析（可带新分类标准）
 * @param {string} groupId
 * @param {Object} data - { classification_criteria }
 */
export const reanalyzeMonteCarloGroup = (groupId, data) => {
  return service.post(`/api/monte-carlo/${groupId}/analyze`, data)
}

/**
 * 停止 Monte Carlo 组
 * @param {Object} data - { group_id }
 */
export const stopMonteCarloGroup = (data) => {
  return service.post('/api/monte-carlo/stop', data)
}

/**
 * 获取子模拟列表
 * @param {string} groupId
 */
export const getMonteCarloChildren = (groupId) => {
  return service.get(`/api/monte-carlo/${groupId}/children`)
}
