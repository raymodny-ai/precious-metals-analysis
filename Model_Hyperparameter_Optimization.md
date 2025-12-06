# 第一部分：推荐模型的参数优化完整指南

## 核心优化策略

### 参数优化方法论（3 阶段）

```
第 1 阶段：粗调（Grid Search）- 1 小时
  ├─ 快速扫描参数空间
  ├─ 找到合理的参数范围
  └─ 成本最低

第 2 阶段：中调（Random Search）- 3-5 小时
  ├─ 在粗调范围内随机采样
  ├─ 计算效率更高
  └─ 找到局部最优

第 3 阶段：精调（Bayesian Optimization）- 5-10 小时
  ├─ 用高斯过程智能搜索
  ├─ 快速收敛到全局最优
  └─ 成本最低 + 准确度最高
```

---

## 1. TabNet 参数优化

### 核心参数说明

```python
TabNet 关键参数（7 个）：

1️⃣ n_independent (默认 2)
   ├─ 含义：独立特征选择掩码的层数
   ├─ 范围：1-4
   ├─ 作用：越大越复杂，但计算量增加
   └─ 建议：小数据 1-2，大数据 2-3

2️⃣ n_shared (默认 2)
   ├─ 含义：共享特征选择掩码的层数
   ├─ 范围：1-4
   ├─ 作用：减少参数，提高泛化
   └─ 建议：与 n_independent 相同或更小

3️⃣ gamma (默认 1.5)
   ├─ 含义：注意力更新的稀疏度
   ├─ 范围：1.0-2.5
   ├─ 作用：控制特征选择的稀疏性
   └─ 建议：1.2-1.8 效果最好

4️⃣ lambda_sparse (默认 0.001)
   ├─ 含义：稀疏性正则化系数
   ├─ 范围：0.0001-0.01
   ├─ 作用：惩罚未使用的特征
   └─ 建议：0.0001-0.001

5️⃣ batch_size (默认 128)
   ├─ 含义：批处理大小
   ├─ 范围：32-512
   ├─ 作用：权衡速度和稳定性
   └─ 建议：256 平衡最好

6️⃣ virtual_batch_size (默认 128)
   ├─ 含义：虚拟批处理大小（Ghost BatchNorm）
   ├─ 范围：32-256
   ├─ 作用：改进批规范化
   └─ 建议：64-128

7️⃣ lambda_l1/l2 (默认 0)
   ├─ 含义：L1/L2 正则化
   ├─ 范围：0.0-0.01
   ├─ 作用：防止过拟合
   └─ 建议：0.0001-0.001
```

### TabNet 参数优化代码

```python
from optuna import create_study
from optuna.samplers import TPESampler
from pytorch_tabnet.tab_model import TabNetRegressor
from sklearn.metrics import mean_squared_error
import numpy as np

class TabNetOptimizer:
    def __init__(self, X_train, y_train, X_val, y_val, random_state=42):
        self.X_train = X_train
        self.y_train = y_train
        self.X_val = X_val
        self.y_val = y_val
        self.random_state = random_state
        self.trials = []
    
    def objective(self, trial):
        """定义优化目标函数"""
        
        # 参数搜索空间
        params = {
            'n_independent': trial.suggest_int('n_independent', 1, 4),
            'n_shared': trial.suggest_int('n_shared', 1, 4),
            'gamma': trial.suggest_float('gamma', 1.0, 2.5, step=0.1),
            'lambda_sparse': trial.suggest_float('lambda_sparse', 1e-4, 1e-2, log=True),
            'batch_size': trial.suggest_categorical('batch_size', [64, 128, 256, 512]),
            'virtual_batch_size': trial.suggest_categorical('virtual_batch_size', [64, 128, 256]),
            'lambda_l1': trial.suggest_float('lambda_l1', 0.0, 1e-2, log=True),
            'lambda_l2': trial.suggest_float('lambda_l2', 0.0, 1e-2, log=True),
            'learning_rate': trial.suggest_float('learning_rate', 0.001, 0.1, log=True)
        }
        
        try:
            # 创建模型
            model = TabNetRegressor(
                n_independent=params['n_independent'],
                n_shared=params['n_shared'],
                gamma=params['gamma'],
                lambda_sparse=params['lambda_sparse'],
                batch_size=params['batch_size'],
                virtual_batch_size=params['virtual_batch_size'],
                lambda_l1=params['lambda_l1'],
                lambda_l2=params['lambda_l2'],
                optimizer_params=dict(lr=params['learning_rate']),
                seed=self.random_state,
                verbose=0
            )
            
            # 训练
            model.fit(
                self.X_train, self.y_train,
                eval_set=[(self.X_val, self.y_val)],
                eval_metric=['rmse'],
                max_epochs=100,
                patience=20,
                batch_size=params['batch_size'],
                virtual_batch_size=params['virtual_batch_size']
            )
            
            # 验证
            y_pred = model.predict(self.X_val)
            rmse = np.sqrt(mean_squared_error(self.y_val, y_pred))
            
            # 记录试验
            self.trials.append({
                'params': params,
                'rmse': rmse,
                'trial': trial.number
            })
            
            return rmse
        
        except Exception as e:
            print(f"Trial {trial.number} failed: {str(e)}")
            return float('inf')
    
    def optimize(self, n_trials=100, timeout=None):
        """运行贝叶斯优化"""
        
        sampler = TPESampler(seed=self.random_state)
        study = create_study(sampler=sampler, direction='minimize')
        
        study.optimize(
            self.objective,
            n_trials=n_trials,
            timeout=timeout,
            show_progress_bar=True
        )
        
        print(f"\n✅ 优化完成！")
        print(f"最佳 RMSE: {study.best_value:.4f}")
        print(f"最佳参数:")
        for key, value in study.best_params.items():
            print(f"  {key}: {value}")
        
        return study
    
    def get_best_model(self, study):
        """获取最优模型"""
        
        best_params = study.best_params
        
        model = TabNetRegressor(
            n_independent=best_params['n_independent'],
            n_shared=best_params['n_shared'],
            gamma=best_params['gamma'],
            lambda_sparse=best_params['lambda_sparse'],
            batch_size=best_params['batch_size'],
            virtual_batch_size=best_params['virtual_batch_size'],
            lambda_l1=best_params['lambda_l1'],
            lambda_l2=best_params['lambda_l2'],
            optimizer_params=dict(lr=best_params['learning_rate']),
            seed=self.random_state,
            verbose=0
        )
        
        model.fit(
            self.X_train, self.y_train,
            eval_set=[(self.X_val, self.y_val)],
            eval_metric=['rmse'],
            max_epochs=200,
            patience=30,
            batch_size=best_params['batch_size'],
            virtual_batch_size=best_params['virtual_batch_size']
        )
        
        return model

# 使用示例
optimizer = TabNetOptimizer(X_train, y_train, X_val, y_val)
study = optimizer.optimize(n_trials=100)
best_model = optimizer.get_best_model(study)
```

### TabNet 推荐参数配置（不同场景）

```python
# MVP 快速版（精度>速度）
TABNET_MVP = {
    'n_independent': 1,
    'n_shared': 1,
    'gamma': 1.3,
    'lambda_sparse': 0.0001,
    'batch_size': 256,
    'virtual_batch_size': 128,
    'lambda_l1': 0.0,
    'lambda_l2': 0.0001,
    'learning_rate': 0.05
}

# 生产版（精度 + 稳定性）
TABNET_PROD = {
    'n_independent': 2,
    'n_shared': 2,
    'gamma': 1.5,
    'lambda_sparse': 0.0005,
    'batch_size': 256,
    'virtual_batch_size': 128,
    'lambda_l1': 0.0001,
    'lambda_l2': 0.0005,
    'learning_rate': 0.01
}

# 企业版（最优精度）
TABNET_ENTERPRISE = {
    'n_independent': 3,
    'n_shared': 2,
    'gamma': 1.8,
    'lambda_sparse': 0.001,
    'batch_size': 512,
    'virtual_batch_size': 256,
    'lambda_l1': 0.0005,
    'lambda_l2': 0.001,
    'learning_rate': 0.001
}
```

---

## 2. XGBoost 参数优化

### 关键参数（10 个）

```python
XGBoost 重要参数优化顺序：

第 1 层（基础参数）：
  1️⃣ max_depth：树的最大深度
     范围：3-15
     建议：5-8（贵金属预测）
  
  2️⃣ learning_rate：学习速率
     范围：0.001-0.3
     建议：0.01-0.1
  
  3️⃣ n_estimators：树的数量
     范围：100-1000
     建议：200-500

第 2 层（正则化参数）：
  4️⃣ subsample：样本采样比例
     范围：0.5-1.0
     建议：0.7-0.9
  
  5️⃣ colsample_bytree：特征采样比例
     范围：0.5-1.0
     建议：0.7-0.9
  
  6️⃣ gamma：最小分裂收益
     范围：0-5
     建议：0.1-1.0
  
  7️⃣ min_child_weight：最小叶子权重
     范围：1-100
     建议：3-10

第 3 层（高级参数）：
  8️⃣ lambda：L2 正则化
     范围：0-5
     建议：0.5-2.0
  
  9️⃣ alpha：L1 正则化
     范围：0-5
     建议：0.0-1.0
  
  🔟 scale_pos_weight：不平衡处理
     范围：自动计算
     建议：pos_num / neg_num
```

### XGBoost 优化代码（Bayesian）

```python
from xgboost import XGBRegressor
from sklearn.metrics import mean_squared_error
from optuna import create_study
from optuna.samplers import TPESampler

class XGBoostOptimizer:
    def __init__(self, X_train, y_train, X_val, y_val, random_state=42):
        self.X_train = X_train
        self.y_train = y_train
        self.X_val = X_val
        self.y_val = y_val
        self.random_state = random_state
    
    def objective(self, trial):
        """贝叶斯优化目标函数"""
        
        # 分阶段优化
        # 第 1 层：树的结构参数
        max_depth = trial.suggest_int('max_depth', 3, 15)
        learning_rate = trial.suggest_float('learning_rate', 0.001, 0.3, log=True)
        n_estimators = trial.suggest_int('n_estimators', 100, 1000, step=50)
        
        # 第 2 层：正则化参数
        subsample = trial.suggest_float('subsample', 0.5, 1.0)
        colsample_bytree = trial.suggest_float('colsample_bytree', 0.5, 1.0)
        gamma = trial.suggest_float('gamma', 0.0, 5.0)
        min_child_weight = trial.suggest_int('min_child_weight', 1, 100)
        
        # 第 3 层：L1/L2 正则化
        reg_lambda = trial.suggest_float('reg_lambda', 0.0, 5.0)
        reg_alpha = trial.suggest_float('reg_alpha', 0.0, 5.0)
        
        try:
            model = XGBRegressor(
                max_depth=max_depth,
                learning_rate=learning_rate,
                n_estimators=n_estimators,
                subsample=subsample,
                colsample_bytree=colsample_bytree,
                gamma=gamma,
                min_child_weight=min_child_weight,
                reg_lambda=reg_lambda,
                reg_alpha=reg_alpha,
                random_state=self.random_state,
                verbose=0
            )
            
            model.fit(
                self.X_train, self.y_train,
                eval_set=[(self.X_val, self.y_val)],
                early_stopping_rounds=50,
                verbose=False
            )
            
            y_pred = model.predict(self.X_val)
            rmse = np.sqrt(mean_squared_error(self.y_val, y_pred))
            
            return rmse
        
        except Exception as e:
            return float('inf')
    
    def optimize(self, n_trials=150):
        """运行优化（通常 5-10 小时）"""
        
        sampler = TPESampler(seed=self.random_state)
        study = create_study(sampler=sampler, direction='minimize')
        
        study.optimize(
            self.objective,
            n_trials=n_trials,
            show_progress_bar=True
        )
        
        return study

# 推荐参数配置
XGBOOST_MVP = {
    'max_depth': 6,
    'learning_rate': 0.05,
    'n_estimators': 300,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'gamma': 0.5,
    'min_child_weight': 5,
    'reg_lambda': 1.0,
    'reg_alpha': 0.5
}

XGBOOST_PROD = {
    'max_depth': 5,
    'learning_rate': 0.01,
    'n_estimators': 500,
    'subsample': 0.75,
    'colsample_bytree': 0.75,
    'gamma': 1.0,
    'min_child_weight': 10,
    'reg_lambda': 2.0,
    'reg_alpha': 1.0
}
```

---

## 3. LSTM + Attention 参数优化

### 关键参数（8 个）

```python
LSTM 超参数说明：

1️⃣ hidden_dim（隐层维度）
   范围：32-256
   建议：64-128
   
2️⃣ num_layers（LSTM 层数）
   范围：1-3
   建议：2
   
3️⃣ batch_size（批处理）
   范围：32-512
   建议：64-128
   
4️⃣ learning_rate（学习率）
   范围：0.0001-0.01
   建议：0.001
   
5️⃣ dropout
   范围：0.0-0.5
   建议：0.2-0.3
   
6️⃣ weight_decay（L2 正则）
   范围：0.0-1e-3
   建议：1e-5
   
7️⃣ gradient_clip（梯度裁剪）
   范围：0.5-5.0
   建议：1.0
   
8️⃣ early_stopping_patience
   范围：10-50
   建议：20-30
```

### LSTM 优化代码

```python
import torch
import torch.nn as nn
from optuna import create_study

class LSTMOptimizer:
    def __init__(self, train_loader, val_loader, device='cuda'):
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.device = device
    
    def objective(self, trial):
        """LSTM 优化目标"""
        
        params = {
            'hidden_dim': trial.suggest_int('hidden_dim', 32, 256, step=32),
            'num_layers': trial.suggest_int('num_layers', 1, 3),
            'dropout': trial.suggest_float('dropout', 0.0, 0.5, step=0.1),
            'learning_rate': trial.suggest_float('learning_rate', 1e-4, 1e-2, log=True),
            'weight_decay': trial.suggest_float('weight_decay', 0.0, 1e-3, log=True),
            'batch_size': trial.suggest_categorical('batch_size', [64, 128, 256])
        }
        
        # 构建模型
        model = LSTMAttentionGoldPredictor(
            input_dim=13,
            hidden_dim=params['hidden_dim'],
            output_dim=5,
            num_layers=params['num_layers']
        ).to(self.device)
        
        optimizer = torch.optim.Adam(
            model.parameters(),
            lr=params['learning_rate'],
            weight_decay=params['weight_decay']
        )
        
        criterion = nn.MSELoss()
        best_val_loss = float('inf')
        patience_count = 0
        patience = 20
        
        # 训练
        for epoch in range(100):
            model.train()
            for X_batch, y_batch in self.train_loader:
                X_batch = X_batch.to(self.device)
                y_batch = y_batch.to(self.device)
                
                predictions, _ = model(X_batch)
                loss = criterion(predictions, y_batch)
                
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
            
            # 验证
            model.eval()
            val_loss = 0
            with torch.no_grad():
                for X_batch, y_batch in self.val_loader:
                    X_batch = X_batch.to(self.device)
                    y_batch = y_batch.to(self.device)
                    predictions, _ = model(X_batch)
                    val_loss += criterion(predictions, y_batch).item()
            
            val_loss /= len(self.val_loader)
            
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_count = 0
            else:
                patience_count += 1
            
            if patience_count >= patience:
                break
        
        return best_val_loss

# 推荐参数
LSTM_MVP = {
    'hidden_dim': 64,
    'num_layers': 2,
    'dropout': 0.2,
    'learning_rate': 0.001,
    'weight_decay': 0.0,
    'batch_size': 128,
    'num_epochs': 100,
    'patience': 20
}

LSTM_PROD = {
    'hidden_dim': 128,
    'num_layers': 2,
    'dropout': 0.3,
    'learning_rate': 0.0005,
    'weight_decay': 1e-5,
    'batch_size': 64,
    'num_epochs': 150,
    'patience': 30
}
```

---

## 4. 集成模型（Ensemble）参数优化

### 权重优化

```python
class EnsembleWeightOptimizer:
    def __init__(self, models, X_val, y_val):
        self.models = models  # [tabnet, lstm, xgb]
        self.X_val = X_val
        self.y_val = y_val
    
    def objective(self, trial):
        """优化集成权重"""
        
        # 权重必须 > 0 且和为 1
        weights = []
        for i in range(len(self.models) - 1):
            w = trial.suggest_float(f'weight_{i}', 0.0, 1.0)
            weights.append(w)
        
        # 最后一个权重使总和为 1
        weights.append(max(0, 1.0 - sum(weights)))
        
        # 如果权重非法，跳过
        if sum(weights) != 1.0 or any(w < 0 for w in weights):
            return float('inf')
        
        # 集成预测
        ensemble_pred = np.zeros_like(self.y_val)
        for i, model in enumerate(self.models):
            pred = model.predict(self.X_val)
            ensemble_pred += weights[i] * pred
        
        rmse = np.sqrt(mean_squared_error(self.y_val, ensemble_pred))
        return rmse

# 优化
from optuna import create_study
from optuna.samplers import TPESampler

sampler = TPESampler(seed=42)
study = create_study(sampler=sampler, direction='minimize')
optimizer = EnsembleWeightOptimizer([tabnet, lstm, xgb], X_val, y_val)

study.optimize(optimizer.objective, n_trials=100)

# 输出最优权重
print(f"最优权重: {study.best_params}")
# 通常结果类似：
# weight_0 (TabNet): 0.40-0.50
# weight_1 (LSTM): 0.25-0.35
# weight_2 (XGBoost): 0.20-0.30
```

---

## 参数优化总结表

| 模型 | 关键参数 | 优化方法 | 时间 | 效果提升 |
|-----|--------|--------|------|---------|
| TabNet | 7 个 | Bayesian | 5-8h | 15-25% |
| XGBoost | 10 个 | Bayesian | 8-12h | 10-20% |
| LSTM | 8 个 | Bayesian | 6-10h | 12-18% |
| Ensemble | 3 个 | Grid | 1-2h | 5-10% |

---

## 完整优化工作流代码

```python
class FullOptimizationPipeline:
    def __init__(self, X_train, y_train, X_val, y_val):
        self.X_train = X_train
        self.y_train = y_train
        self.X_val = X_val
        self.y_val = y_val
        self.models = {}
    
    def optimize_all(self):
        """优化所有模型（总耗时 20-30 小时）"""
        
        print("🚀 开始模型参数优化...")
        
        # 步骤 1：优化 TabNet
        print("\n📊 优化 TabNet (预计 5-8 小时)...")
        tabnet_optimizer = TabNetOptimizer(
            self.X_train, self.y_train,
            self.X_val, self.y_val
        )
        tabnet_study = tabnet_optimizer.optimize(n_trials=100)
        self.models['tabnet'] = tabnet_optimizer.get_best_model(tabnet_study)
        
        # 步骤 2：优化 XGBoost
        print("\n📊 优化 XGBoost (预计 8-12 小时)...")
        xgb_optimizer = XGBoostOptimizer(
            self.X_train, self.y_train,
            self.X_val, self.y_val
        )
        xgb_study = xgb_optimizer.optimize(n_trials=150)
        
        # 步骤 3：优化 LSTM
        print("\n📊 优化 LSTM+Attention (预计 6-10 小时)...")
        lstm_optimizer = LSTMOptimizer(train_loader, val_loader)
        lstm_study = lstm_optimizer.optimize(n_trials=100)
        
        # 步骤 4：优化集成权重
        print("\n📊 优化 Ensemble 权重 (预计 1-2 小时)...")
        ensemble_optimizer = EnsembleWeightOptimizer(
            [self.models['tabnet'], lstm_model, xgb_model],
            self.X_val, self.y_val
        )
        ensemble_study = create_study(direction='minimize')
        ensemble_study.optimize(ensemble_optimizer.objective, n_trials=100)
        
        print("\n✅ 所有模型优化完成！")
        
        return {
            'tabnet_study': tabnet_study,
            'xgb_study': xgb_study,
            'lstm_study': lstm_study,
            'ensemble_study': ensemble_study
        }
    
    def save_best_params(self, studies, filepath):
        """保存最优参数"""
        
        import json
        
        best_params = {
            'tabnet': studies['tabnet_study'].best_params,
            'xgboost': studies['xgb_study'].best_params,
            'lstm': studies['lstm_study'].best_params,
            'ensemble': studies['ensemble_study'].best_params
        }
        
        with open(filepath, 'w') as f:
            json.dump(best_params, f, indent=2)
        
        print(f"✅ 参数已保存到 {filepath}")
```

---

## 参考资源

1. Bayesian Optimization[232]：https://aiinpractice.com/xgboost-hyperparameter-tuning-with-bayesian-optimization/
2. PyTorch TabNet 参数[236]：https://pytorch-tabular.readthedocs.io
3. XGBoost/LightGBM 调参[235]：https://jatit.org/volumes/Vol102No9/32Vol102No9.pdf
4. Optuna 文档：https://optuna.readthedocs.io