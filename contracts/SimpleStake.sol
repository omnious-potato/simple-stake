pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC1155/ERC1155.sol";
import "@openzeppelin/contracts/token/ERC1155/utils/ERC1155Holder.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

import "@chainlink/contracts/src/v0.8/VRFConsumerBase.sol";

contract StakeToken is ERC1155, ERC1155Holder, VRFConsumerBase, Ownable {
    address public recentWinner;
    uint256 public constant BRONZE = 0;
    uint256 public constant SILVER = 1;
    uint256 public constant GOLD = 2;
    uint256 public constant PLATINUM = 3;

    bytes32 public keyhash;
    uint256 public fee;

    uint256[] public INITIAL_MINT_IDS = [BRONZE, SILVER, GOLD];

    uint256[] public tokenBaseValue = [1, 100, 10000];

    enum STAKE_STATUS {
        OPEN,
        CLOSED,
        CHOOSING_RANDOM,
        CALCULATING_PAYOUT
    }

    event RequestedRandomness(bytes32 requestId);
    mapping(bytes32 => uint256) public randomnessByRequest;

    constructor(
        address _vrfCoordinator,
        address _link,
        uint256 _fee,
        bytes32 _keyhash,
        uint256 _bronze,
        uint256 _silver,
        uint256 _gold
    ) ERC1155("") VRFConsumerBase(_vrfCoordinator, _link) {
        fee = _fee;
        keyhash = _keyhash;

        timed_stake_status = STAKE_STATUS.CLOSED;

        totalTickets = 0;
        timed_withheld_tokens = [0, 0, 0];
        timedIndexIncrement = 0;

        uint256[] memory _supply = new uint256[](3);
        _supply[0] = _bronze;
        _supply[1] = _silver;
        _supply[2] = _gold;

        _mintBatch(address(this), INITIAL_MINT_IDS, _supply, "0x0");
        _mintBatch(owner(), INITIAL_MINT_IDS, _supply, "0x0"); //remove later
    }

    STAKE_STATUS public timed_stake_status;
    uint256[] public timed_stake_accepts = [BRONZE, SILVER, GOLD];
    uint256 public totalTickets;
    uint256 timed_stake_end;
    uint256[] timed_withheld_tokens;
    uint256 public timedIndexIncrement;

    mapping(address => uint256) public ticketsByAddress;
    mapping(uint256 => address) public addressByIndex;

    function start_timed_stake(uint256 timed_stake_duration) public {
        require(
            timed_stake_status == STAKE_STATUS.CLOSED,
            "Can't start timed stake yet!"
        );
        timed_stake_end = block.timestamp + timed_stake_duration;
        timed_stake_status = STAKE_STATUS.OPEN;
    }

    function enter_timed_stake(uint256 token_id, uint256 amount) public {
        require(
            timed_stake_status == STAKE_STATUS.OPEN,
            "Stake is closed now!"
        ); //stake should be opened to enter

        require(
            balanceOf(msg.sender, token_id) >= amount,
            "Not enough tokens of that type on balance"
        ); //ensure that sender has enough tokens

        require(block.timestamp <= timed_stake_end, "Stake is alredy due!");

        safeTransferFrom(msg.sender, address(this), token_id, amount, "0x0");
        timed_withheld_tokens[token_id] += amount;
        ticketsByAddress[msg.sender] = amount * tokenBaseValue[token_id];
        addressByIndex[timedIndexIncrement] = msg.sender;

        timedIndexIncrement++;

        totalTickets += ticketsByAddress[msg.sender];
    }

    bytes32 public timedRequestId;

    function end_timed_stake() public {
        require(
            block.timestamp >= timed_stake_end,
            "Stake hasn't expired yet!"
        );
        timed_stake_status = STAKE_STATUS.CHOOSING_RANDOM;
        timedRequestId = requestRandomness(keyhash, fee);

        emit RequestedRandomness(timedRequestId);
    }

    function timed_calculate_and_payout(bytes32 requestId) public onlyOwner {
        require(timed_stake_status == STAKE_STATUS.CALCULATING_PAYOUT);
        require(randomnessByRequest[requestId] > 0);

        uint256 winning_ticket = randomnessByRequest[requestId] % totalTickets;
        uint256 ticketRange = ticketsByAddress[addressByIndex[0]];
        uint256 i = 0;
        while (winning_ticket > ticketRange) {
            i++;
            ticketRange += ticketsByAddress[addressByIndex[i]];
        }

        recentWinner = addressByIndex[i];

        safeBatchTransferFrom(
            address(this),
            recentWinner,
            timed_stake_accepts,
            timed_withheld_tokens,
            "0x0"
        );

        for (uint256 j = 0; j < timedIndexIncrement; j++) {
            ticketsByAddress[addressByIndex[j]] = 0;
            addressByIndex[j] = address(0);
        }

        totalTickets = 0;
        timedIndexIncrement = 0;
        timed_withheld_tokens = [0, 0, 0];

        timed_stake_status = STAKE_STATUS.CLOSED;
    }

    function fulfillRandomness(bytes32 _requestId, uint256 _randomness)
        internal
        override
    {
        require(
            timed_stake_status == STAKE_STATUS.CHOOSING_RANDOM,
            "Stake isn't here yet!"
        );
        require(_randomness > 0);
        randomnessByRequest[_requestId] = _randomness;
        timed_stake_status = STAKE_STATUS.CALCULATING_PAYOUT;
    }

    function supportsInterface(bytes4 interfaceId)
        public
        view
        virtual
        override(ERC1155, ERC1155Receiver)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
