/**
 * Test fixture with class methods and arrow functions.
 */

class EventEmitter {
    constructor() {
        this.listeners = {};
    }

    on(event, callback) {
        if (!this.listeners[event]) {
            this.listeners[event] = [];
        }
        this.listeners[event].push(callback);
    }
}

const handleRequest = (req, res) => {
    const body = req.body;
    res.send(body);
};

// Top-level code (not inside any definition)
const x = 1;
