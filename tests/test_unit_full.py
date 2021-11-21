import time

from brownie.network import contract
from scripts.functions import (
    LOCAL_BLOCKCHAIN_ENVIRONMENTS,
    FORKED_LOCAL_ENVIRONMENTS,
    get_account,
    fund_with_link,
    get_contract,
)
from brownie import StakeToken, accounts, config, network, exceptions
from scripts.create_and_deploy_basics import balances, create_and_mint
from web3 import Web3
import pytest


TEST_MINT_SUPPLY = [1000000, 1000000, 1000000]
STAKE_VALID_TIME = 2
TX_AMOUNT = 100


def test_can_deploy_and_mint_at_owner():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()

    contract = create_and_mint(
        TEST_MINT_SUPPLY[0], TEST_MINT_SUPPLY[1], TEST_MINT_SUPPLY[2]
    )

    ownerBalance = contract.balanceOfBatch([contract.owner()] * 3, [0, 1, 2])

    assert ownerBalance == TEST_MINT_SUPPLY


def test_can_transfer_directly_and_approved():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()

    contract = create_and_mint(
        TEST_MINT_SUPPLY[0], TEST_MINT_SUPPLY[1], TEST_MINT_SUPPLY[2]
    )

    owner = contract.owner()

    TX_TOKEN_ID = 0

    sender = get_account(2)
    receiver = get_account(3)

    contract.safeTransferFrom(
        owner, sender, TX_TOKEN_ID, TX_AMOUNT, "0x0", {"from": owner}
    )

    with pytest.raises(exceptions.VirtualMachineError):
        contract.safeTransferFrom(
            sender, receiver, TX_TOKEN_ID, TX_AMOUNT, "0x0", {"from": owner}
        )

    contract.safeTransferFrom(
        sender, receiver, TX_TOKEN_ID, TX_AMOUNT / 2, "0x0", {"from": sender}
    )

    contract.setApprovalForAll(owner, True, {"from": sender})

    contract.safeTransferFrom(
        sender, receiver, TX_TOKEN_ID, TX_AMOUNT / 2, "0x0", {"from": owner}
    )

    senderBalance = contract.balanceOf(sender, 0)
    receiverBalance = contract.balanceOf(receiver, 0)

    assert senderBalance == 0 and receiverBalance == TX_AMOUNT


def test_can_start_and_enter_timed_stake():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()

    contract = create_and_mint(
        TEST_MINT_SUPPLY[0], TEST_MINT_SUPPLY[1], TEST_MINT_SUPPLY[2]
    )

    owner = contract.owner()

    players = [get_account(1), get_account(2), get_account(3)]

    contract.safeTransferFrom(
        owner,
        players[0],
        0,
        TX_AMOUNT * contract.tokenBaseValue(0),
        "0x0",
        {"from": owner},
    )
    contract.safeTransferFrom(
        owner,
        players[1],
        1,
        TX_AMOUNT * contract.tokenBaseValue(1),
        "0x0",
        {"from": owner},
    )
    contract.safeTransferFrom(
        owner,
        players[2],
        2,
        TX_AMOUNT * contract.tokenBaseValue(2),
        "0x0",
        {"from": owner},
    )

    contract.start_timed_stake(STAKE_VALID_TIME, {"from": players[0]})

    contract.enter_timed_stake(
        0, TX_AMOUNT * contract.tokenBaseValue(0), {"from": players[0]}
    )
    contract.enter_timed_stake(
        1, TX_AMOUNT * contract.tokenBaseValue(1), {"from": players[1]}
    )
    contract.enter_timed_stake(
        2, TX_AMOUNT * contract.tokenBaseValue(2), {"from": players[2]}
    )

    assert (
        contract.addressByIndex(0) == players[0]
        and contract.addressByIndex(1) == players[1]
        and contract.addressByIndex(2) == players[2]
    )


def test_can_end_timed_stake():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()

    contract = create_and_mint(
        TEST_MINT_SUPPLY[0], TEST_MINT_SUPPLY[1], TEST_MINT_SUPPLY[2]
    )

    owner = contract.owner()

    contract.start_timed_stake(STAKE_VALID_TIME, {"from": owner})
    contract.enter_timed_stake(0, 1000, {"from": owner})

    fund_with_link(contract)
    time.sleep(STAKE_VALID_TIME)

    contract.end_timed_stake({"from": owner})

    assert contract.timed_stake_status() == 2


def test_can_choose_winner():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()

    contract = create_and_mint(
        TEST_MINT_SUPPLY[0], TEST_MINT_SUPPLY[1], TEST_MINT_SUPPLY[2]
    )

    owner = contract.owner()

    TOKEN_VALUE = 1

    players = [get_account(3), get_account(4), get_account(5), get_account(6)]

    for index in range(len(players)):
        contract.safeTransferFrom(
            owner, players[index], 0, TX_AMOUNT, "0x0", {"from": owner}
        )

    contract.start_timed_stake(STAKE_VALID_TIME, {"from": owner})

    for index in range(len(players)):
        contract.enter_timed_stake(0, TX_AMOUNT, {"from": players[index]})

    fund_with_link(contract)

    time.sleep(STAKE_VALID_TIME)
    tx = contract.end_timed_stake({"from": players[0]})
    request_id = tx.events["RequestedRandomness"]["requestId"]

    STATIC_MAGIC_NUMBER = 1337

    get_contract("vrf_coordinator").callBackWithRandomness(
        request_id, STATIC_MAGIC_NUMBER, contract.address, {"from": owner}
    )

    for i in range(len(players)):
        print(contract.addressByIndex(i))

    contract.timed_calculate_and_payout(contract.timedRequestId(), {"from": owner})

    TOTAL_TICKETS = TX_AMOUNT * len(players) * TOKEN_VALUE
    WINNING_TICKET = STATIC_MAGIC_NUMBER % TOTAL_TICKETS

    TICKET_OFFSET = 100
    WINNER_INDEX = 1
    while WINNING_TICKET > TICKET_OFFSET:
        TICKET_OFFSET += TX_AMOUNT
        WINNER_INDEX += 1

    WINNER_INDEX -= 1

    print(f"Winner is:{contract.recentWinner()}")
    assert contract.recentWinner() == players[WINNER_INDEX]
    assert (
        contract.balanceOf(contract.recentWinner(), 0)
        == TX_AMOUNT * len(players) * TOKEN_VALUE
    )
    return contract
