# ERC1155 токен со ставками
## Контракт в сети
Тестовый контракт в тестнете (Rinkeby) - <a href='https://rinkeby.etherscan.io/address/0xD7Ff1c0f62dd594118Af84844d3E016C9328e4c0'>0xD7Ff1c0f62dd594118Af84844d3E016C9328e4c0</a>
## Функционал
### Пари
Ограниченные по времени пари, в которых шансы игроков пропорциональны их ставкам. 

Игроки могут ставить три типа "фишек" (бронзовых, серебрянных, золотых - относительным соотношением номиналов 10000:100:1 соответственно). 
По истечению времени игроки больше не могут участовать в этой ставке, и владелец контракта может запросить случайное число c помощью <a href='https://docs.chain.link/docs/chainlink-vrf/'></a>.

Далее, владелец вызывает функцию по вычислению победителя и производит выплату в фишках
### Будущий функционал
#### Обмен "фишек" на эфир
## Текущие проблемы
1. Из-за особенностей стандарта ERC1155 в контракте нельзя провести переводы с самого "счета" контракта или между игроками внутри контракта без вызова самого владельца средств или разрешенных ему. Поэтому, планируется разделение текущего контракта токена на три части - сам контракт с базовыми операциями создания и трансфера игровых и неигровых монет, игровой части и обменной части.

2. Из-за итеративного алгоритма вычисления победителя в ставке затрачивается много вычислительного ресура, а соответсвенно и стоимость самой транзакции сильно повышается (на текущий момент, в реальной сети стоимость вычисления победителя по такому контракту будет примерно равна $100\text{gwei}\cdot 2 \cdot 10^5 = 0.02 \text{ETH}$ (по текущему курсу около $90)
