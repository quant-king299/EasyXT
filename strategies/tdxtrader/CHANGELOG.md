# CHANGELOG


## v0.4.5 (2025-02-08)

### Bug Fixes

- 修改文档错误
  ([`a288e6b`](https://github.com/zsrl/tdxtrader/commit/a288e6b2aa714cf1d80de34d4de37adcda18ba5e))


## v0.4.4 (2025-02-08)

### Performance Improvements

- 买入卖出信号支持多个
  ([`d0cefc2`](https://github.com/zsrl/tdxtrader/commit/d0cefc2e80d5e098ff8a330fe293ee63f89358d9))


## v0.4.3 (2025-01-24)

### Bug Fixes

- 解决读取文件编码错误
  ([`bdf8baf`](https://github.com/zsrl/tdxtrader/commit/bdf8baf15f93d8fc6e33556020d3f3d1c16361c9))


## v0.4.2 (2024-12-19)

### Bug Fixes

- 修改a为ａ
  ([`85aac2d`](https://github.com/zsrl/tdxtrader/commit/85aac2d5b8964cf5cc0fde9417a6884803149872))

### Performance Improvements

- 测试文档站
  ([`71d483a`](https://github.com/zsrl/tdxtrader/commit/71d483af308da97641e746280dca947f3898154d))


## v0.4.1 (2024-12-17)

### Performance Improvements

- 文档站初始化
  ([`b07df14`](https://github.com/zsrl/tdxtrader/commit/b07df143b25cf7016f10d4871b8cf153846f8dea))


## v0.4.0 (2024-12-16)

### Features

- 更改文件读取逻辑，从源头解决错误行的问题
  ([`64da527`](https://github.com/zsrl/tdxtrader/commit/64da527d006a7d6dcbd4b50d0596a3337649cd0e))

### Performance Improvements

- 优化买入卖出事件入参
  ([`ed681d1`](https://github.com/zsrl/tdxtrader/commit/ed681d103e0d6e034a85432e1bc8d823d5feffed))


## v0.3.10 (2024-12-12)

### Bug Fixes

- 修改文件编码为gbk
  ([`f603429`](https://github.com/zsrl/tdxtrader/commit/f60342951b5f37e89b8ad13c0b8da26ad505c1d0))


## v0.3.9 (2024-12-12)

### Bug Fixes

- 删除print
  ([`fb47cdc`](https://github.com/zsrl/tdxtrader/commit/fb47cdc576cb47d6e7a80065354246f1134ec0e0))

- 启动时增加预置表头，解决预警文件首行报错的问题
  ([`f86efcc`](https://github.com/zsrl/tdxtrader/commit/f86efcc41b400b3f44ec1dff880288b7b72ed269))


## v0.3.8 (2024-12-09)

### Bug Fixes

- Qmt查询单持仓的api对etf有bug，已改为查询全部持仓
  ([`3d777b0`](https://github.com/zsrl/tdxtrader/commit/3d777b06e663d1fa5f91264b6da405900921e3d1))


## v0.3.7 (2024-12-08)

### Performance Improvements

- 买入事件增加持仓参数
  ([`4388927`](https://github.com/zsrl/tdxtrader/commit/4388927e9878e59320d7f385d080245a9c6e8d4b))


## v0.3.6 (2024-12-07)

### Bug Fixes

- 修复委托失败报错
  ([`504d0f9`](https://github.com/zsrl/tdxtrader/commit/504d0f926a200e369f662653938ff2df1793b64e))

### Performance Improvements

- 1. 日志报错只打印一次。2. 当买入或卖出时间返回None时不下单
  ([`ce18f4b`](https://github.com/zsrl/tdxtrader/commit/ce18f4b7797681affdaa6592ad11072c22a9c477))


## v0.3.5 (2024-12-04)

### Bug Fixes

- 删除不必要的输出
  ([`94be2f6`](https://github.com/zsrl/tdxtrader/commit/94be2f6fa349f3d183a5745d4c199277a2985b4e))


## v0.3.4 (2024-12-04)

### Bug Fixes

- 解决语法错误
  ([`7142fae`](https://github.com/zsrl/tdxtrader/commit/7142fae663de6f735e6642b2806e3ae1d2356feb))


## v0.3.3 (2024-12-04)

### Bug Fixes

- 处理南京港报错
  ([`c6a536f`](https://github.com/zsrl/tdxtrader/commit/c6a536f3e1455de7aef932fa2e240dd7fc232686))


## v0.3.2 (2024-12-03)

### Bug Fixes

- 图片打码
  ([`119d23d`](https://github.com/zsrl/tdxtrader/commit/119d23d3c1f8f62273b7148ef1802956a14319a7))


## v0.3.1 (2024-12-03)

### Performance Improvements

- 优化文档
  ([`980177d`](https://github.com/zsrl/tdxtrader/commit/980177d2aa4a411dba9cecd205610b086ad7081c))


## v0.3.0 (2024-12-03)

### Features

- 增加企业微信消息推送
  ([`4b5e3fb`](https://github.com/zsrl/tdxtrader/commit/4b5e3fbec16f7aa75692d7e04f6175c70913a349))

### Performance Improvements

- 优化日志
  ([`db14fc8`](https://github.com/zsrl/tdxtrader/commit/db14fc8596b9ac3972e0d01c034780e786f36b79))


## v0.2.2 (2024-12-03)

### Performance Improvements

- 优化测试
  ([`ffb1f3d`](https://github.com/zsrl/tdxtrader/commit/ffb1f3d66ef7d28de432408a8e3cff4d070c69be))

- 优化输出
  ([`ca26e4a`](https://github.com/zsrl/tdxtrader/commit/ca26e4a67d2d2d943711e227697492b9ec43240b))

- 增加按金额下单
  ([`e915b9f`](https://github.com/zsrl/tdxtrader/commit/e915b9fda4873551a61ec3490432794eae5cd470))


## v0.2.1 (2024-12-01)

### Bug Fixes

- 解决非交易日时间戳不对导致撤单判断有问题
  ([`14ff6ed`](https://github.com/zsrl/tdxtrader/commit/14ff6ed36aee49f73767041ecc8187278cfeeec3))


## v0.2.0 (2024-11-28)

### Features

- 增加自动撤单功能
  ([`62602fe`](https://github.com/zsrl/tdxtrader/commit/62602fe5c59a0b9d7c577e312fb339da12ff334e))

### Performance Improvements

- 监听可撤单的委托
  ([`1c3ae87`](https://github.com/zsrl/tdxtrader/commit/1c3ae874824906fad6a7a353c879d95ca09c7337))


## v0.1.7 (2024-11-27)


## v0.1.6 (2024-11-27)

### Bug Fixes

- 修改没有持仓时卖出报错
  ([`174e690`](https://github.com/zsrl/tdxtrader/commit/174e69010a9b3c8912714452e431945ff819b13f))

### Performance Improvements

- 优化异常捕获，下单报错不影响程序运行
  ([`06fb844`](https://github.com/zsrl/tdxtrader/commit/06fb8449ea50d5a92158befe03a8afec43396c68))


## v0.1.5 (2024-11-27)

### Performance Improvements

- 优化时间输出格式
  ([`fab0845`](https://github.com/zsrl/tdxtrader/commit/fab0845c1b1556eab41f42d02d721f33cdc82034))


## v0.1.4 (2024-11-26)

### Bug Fixes

- 修改
  ([`818e27b`](https://github.com/zsrl/tdxtrader/commit/818e27b1ec45014201503210eeaa7c7b403d4f90))

- 删除描述
  ([`99e0797`](https://github.com/zsrl/tdxtrader/commit/99e0797f1e3827e5266343df20c5265f78214894))


## v0.1.3 (2024-11-26)

### Bug Fixes

- 增加配置
  ([`403b6c1`](https://github.com/zsrl/tdxtrader/commit/403b6c1ebeaa4bdd60490aeab29a1ee5330535b2))


## v0.1.2 (2024-11-26)

### Bug Fixes

- 增加描述
  ([`2129ef0`](https://github.com/zsrl/tdxtrader/commit/2129ef061731a9e281398427f6d0a92ea5efc920))


## v0.1.1 (2024-11-26)

### Bug Fixes

- 调整版本号定义
  ([`cb0397c`](https://github.com/zsrl/tdxtrader/commit/cb0397c29cc8a69f3a9219aab06d6f210a427330))

### Performance Improvements

- 更新文档
  ([`73e6206`](https://github.com/zsrl/tdxtrader/commit/73e62065e1423fe173d5d731069a160f7c9be9a8))


## v0.1.0 (2024-11-26)

### Bug Fixes

- 删除多余的代码
  ([`3b901df`](https://github.com/zsrl/tdxtrader/commit/3b901dfeefcc098a1117dd2d4ed24c52025db95f))

- 发布修改
  ([`c5c0009`](https://github.com/zsrl/tdxtrader/commit/c5c0009de9638c61ab5be8ade130c6bd95a29a48))

- 解决农产品等带空格的股票报错
  ([`2eaabb6`](https://github.com/zsrl/tdxtrader/commit/2eaabb6338d5031dc9354e8eb18196d315ce9c9f))

### Features

- 完成初版
  ([`b10f618`](https://github.com/zsrl/tdxtrader/commit/b10f618dad3eace3343276647c35e61e8d7beae2))

### Performance Improvements

- 增加github actions
  ([`0289f6f`](https://github.com/zsrl/tdxtrader/commit/0289f6f9cad40d138d852d85ac3cf36e376d87a5))

- 增加说明
  ([`6909721`](https://github.com/zsrl/tdxtrader/commit/690972115231a23d1091e47ee692de9977189082))
