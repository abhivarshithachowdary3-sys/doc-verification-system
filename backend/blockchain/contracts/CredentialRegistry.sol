// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title CredentialRegistry
 * @notice Immutable on-chain registry for verified document hashes.
 *         Each SHA-256 hash is stored exactly once, with a timestamp and
 *         the address of the registrar.
 * @dev    Deployed via backend/blockchain/deployer.py using Hardhat/Ganache.
 */
contract CredentialRegistry {

    struct Record {
        bool      registered;
        uint256   timestamp;
        address   registeredBy;
    }

    mapping(bytes32 => Record) private _records;
    address public immutable owner;

    event Registered(bytes32 indexed docHash, address indexed registrar, uint256 timestamp);

    error AlreadyRegistered(bytes32 docHash);
    error Unauthorized();

    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /**
     * @notice Register a new document hash on-chain.
     * @param docHash SHA-256 hash of the verified document fields.
     */
    function register(bytes32 docHash) external onlyOwner {
        if (_records[docHash].registered) revert AlreadyRegistered(docHash);
        _records[docHash] = Record({
            registered:   true,
            timestamp:    block.timestamp,
            registeredBy: msg.sender
        });
        emit Registered(docHash, msg.sender, block.timestamp);
    }

    /**
     * @notice Check whether a hash has been registered.
     */
    function isRegistered(bytes32 docHash) external view returns (bool) {
        return _records[docHash].registered;
    }

    /**
     * @notice Retrieve the full registration record for a hash.
     */
    function getRecord(bytes32 docHash) external view returns (Record memory) {
        return _records[docHash];
    }
}
