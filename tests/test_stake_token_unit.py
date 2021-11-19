import time
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


def test_can_deploy_and_mint():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()

    contract = create_and_mint(
        TEST_MINT_SUPPLY[0], TEST_MINT_SUPPLY[1], TEST_MINT_SUPPLY[2]
    )

    contractBalance = contract.balanceOfBatch([contract.address] * 3, [0, 1, 2])

    assert (
        contractBalance[0] == TEST_MINT_SUPPLY[0]
        and contractBalance[1] == TEST_MINT_SUPPLY[1]
        and contractBalance[2] == TEST_MINT_SUPPLY[2]
    )


def test_can_transfer_from_contract_approved():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()

    contract = create_and_mint(
        TEST_MINT_SUPPLY[0], TEST_MINT_SUPPLY[1], TEST_MINT_SUPPLY[2]
    )

    owner = accounts.at(contract.owner())

    contract.setApprovalForAll(owner.address, True, {"from": contract.address})

    TX_BASE_AMOUNT = 100

    ownerOldBalance = contract.balanceOfBatch([owner.address] * 3, [0, 1, 2])

    contract.safeTransferFrom(contract.address, owner, 0, 100, "0x0", {"from": owner})

    contract.safeBatchTransferFrom(
        contract.address, owner, [0, 1, 2], [TX_BASE_AMOUNT] * 3, "0x0", {"from": owner}
    )

    ownerBalance = contract.balanceOfBatch([owner.address] * 3, [0, 1, 2])

    assert (
        ownerBalance[0] - ownerOldBalance[0] == 2 * TX_BASE_AMOUNT
        and ownerBalance[1] - ownerOldBalance[1] == TX_BASE_AMOUNT
        and ownerBalance[2] - ownerOldBalance[2] == TX_BASE_AMOUNT
    )


def test_cant_transfer_from_contract_nonapproved():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()

    contract = create_and_mint(
        TEST_MINT_SUPPLY[0], TEST_MINT_SUPPLY[1], TEST_MINT_SUPPLY[2]
    )

    owner = accounts.at(contract.owner())

    TX_BASE_AMOUNT = 100

    non_owner = get_account(3)

    assert (
        owner != non_owner
        and contract.isApprovedForAll(contract.address, non_owner) == False
    )

    with pytest.raises(exceptions.VirtualMachineError):
        contract.safeTransferFrom(
            contract.address, non_owner, 0, TX_BASE_AMOUNT, "0x0", {"from": non_owner}
        )


def test_can_transfer_from_user_to_user():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()

    contract = create_and_mint(
        TEST_MINT_SUPPLY[0], TEST_MINT_SUPPLY[1], TEST_MINT_SUPPLY[2]
    )

    user_first = get_account(7)
    trusted_user = get_account(6)
    user_second = get_account(8)

    TX_AMOUNT = 1000

    contract.safeTransferFrom(
        contract.address, user_first, 0, TX_AMOUNT, "0x0", {"from": contract}
    )

    contract.safeTransferFrom(
        user_first, user_second, 0, TX_AMOUNT / 2, "0x0", {"from": user_first}
    )

    with pytest.raises(exceptions.VirtualMachineError):
        contract.safeTransferFrom(
            user_first,
            user_second,
            0,
            TX_AMOUNT / 2,
            "0x0",
            {"from": trusted_user},
        )

    contract.setApprovalForAll(trusted_user, True, {"from": user_first})

    contract.safeTransferFrom(
        user_first,
        user_second,
        0,
        TX_AMOUNT / 4,
        "0x0",
        {"from": trusted_user},
    )

    contract.setApprovalForAll(trusted_user, False, {"from": user_first})

    with pytest.raises(exceptions.VirtualMachineError):
        contract.safeTransferFrom(
            user_first,
            user_second,
            0,
            TX_AMOUNT / 4,
            "0x0",
            {"from": trusted_user},
        )


def test_can_start_and_enter_timed_stake():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()

    contract = create_and_mint(
        TEST_MINT_SUPPLY[0], TEST_MINT_SUPPLY[1], TEST_MINT_SUPPLY[2]
    )

    players = [get_account(3), get_account(4), get_account(5)]

    owner = accounts.at(contract.owner())
    contract.setApprovalForAll(owner, True, {"from": contract})

    contract.safeTransferFrom(contract, players[0], 0, 10000, "0x0", {"from": owner})
    contract.safeTransferFrom(contract, players[1], 1, 100, "0x0", {"from": owner})
    contract.safeTransferFrom(contract, players[2], 2, 1, "0x0", {"from": owner})

    contract.start_timed_stake(STAKE_VALID_TIME, {"from": players[0]})

    contract.enter_timed_stake(0, 10000, {"from": players[0]})
    contract.enter_timed_stake(1, 100, {"from": players[1]})
    contract.enter_timed_stake(2, 1, {"from": players[2]})

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

    owner = accounts.at(contract.owner())
    contract.setApprovalForAll(owner, True, {"from": contract})

    contract.safeTransferFrom(contract, owner, 0, 1000, "0x0", {"from": owner})

    contract.start_timed_stake(STAKE_VALID_TIME, {"from": owner})
    contract.enter_timed_stake(0, 1000, {"from": owner})
    fund_with_link(contract)
    time.sleep(STAKE_VALID_TIME)
    contract.end_timed_stake({"from": owner})
    assert contract.timed_stake_status() == 2


def test_can_choose_winner_correctly():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()

    contract = create_and_mint(
        TEST_MINT_SUPPLY[0], TEST_MINT_SUPPLY[1], TEST_MINT_SUPPLY[2]
    )

    owner = accounts.at(contract.owner())
    contract.setApprovalForAll(owner, True, {"from": contract})

    TX_AMOUNT = 100
    TOKEN_VALUE = 1

    players = [get_account(3), get_account(4), get_account(5), get_account(6)]

    for index in range(len(players)):
        contract.safeTransferFrom(
            contract, players[index], 0, TX_AMOUNT, "0x0", {"from": owner}
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


def test_can_restart_lottery():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()

    contract = create_and_mint(
        TEST_MINT_SUPPLY[0], TEST_MINT_SUPPLY[1], TEST_MINT_SUPPLY[2]
    )

    owner = accounts.at(contract.owner())
    contract.setApprovalForAll(owner, True, {"from": contract})
    contract.safeTransferFrom(contract, owner, 0, 1000, "0x0", {"from": owner})

    contract.start_timed_stake(STAKE_VALID_TIME, {"from": owner})
    contract.enter_timed_stake(0, 100, {"from": owner})

    time.sleep(STAKE_VALID_TIME)
    fund_with_link(contract)
    tx_first = contract.end_timed_stake()

    request_id = tx_first.events["RequestedRandomness"]["requestId"]

    STATIC_MAGIC_NUMBER = 777

    get_contract("vrf_coordinator").callBackWithRandomness(
        request_id, STATIC_MAGIC_NUMBER, contract.address, {"from": owner}
    )

    print(
        f"R:{contract.timedRequestId()}||V:{contract.randomnessByRequest(contract.timedRequestId())}"
    )

    contract.timed_calculate_and_payout(contract.timedRequestId())

    contract.start_timed_stake(STAKE_VALID_TIME, {"from": owner})
    contract.enter_timed_stake(0, 100, {"from": owner})

    time.sleep(STAKE_VALID_TIME)
    fund_with_link(contract)
    tx_second = contract.end_timed_stake()

    second_request_id = tx_second.events["RequestedRandomness"]["requestId"]

    STATIC_MAGIC_NUMBER = 1

    get_contract("vrf_coordinator").callBackWithRandomness(
        second_request_id, STATIC_MAGIC_NUMBER, contract.address, {"from": owner}
    )

    print(
        f"R:{contract.timedRequestId()}||V:{contract.randomnessByRequest(contract.timedRequestId())}"
    )

    contract.timed_calculate_and_payout(contract.timedRequestId())

    assert contract.recentWinner() == owner
    assert (
        contract.timedIndexIncrement() == 0
        and contract.ticketsByAddress(owner) == 0
        and contract.addressByIndex(0) == "0x0000000000000000000000000000000000000000"
    )
    assert contract.timed_stake_status() == 1
