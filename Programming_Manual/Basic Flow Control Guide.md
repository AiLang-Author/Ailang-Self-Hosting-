# Basic Flow Control Guide

## Welcome to Programming with AI Lang!

This guide will teach you how to control the flow of your programs. Flow control is how you tell your program to make decisions, repeat actions, and choose different paths based on conditions.

**No programming experience needed!** We'll start from the very beginning.

---

## Table of Contents

1. [What is Flow Control?](#what-is-flow-control)
2. [Making Decisions with IfCondition](#making-decisions-with-ifcondition)
3. [Repeating Actions with WhileLoop](#repeating-actions-with-whileloop)
4. [Choosing Paths with Fork](#choosing-paths-with-fork)
5. [Multiple Choices with Branch](#multiple-choices-with-branch)
6. [Loop Control](#loop-control)
7. [Practice Exercises](#practice-exercises)
8. [Common Mistakes](#common-mistakes)
9. [Next Steps](#next-steps)

---

## What is Flow Control?

Imagine you're following a recipe. Sometimes you need to make decisions:

- **If** the oven is hot, put the cake in
- **While** the timer hasn't gone off, wait
- **Choose** between chocolate or vanilla

Flow control lets your program make similar decisions!

### Your First Program

Let's start simple:

```ailang
PrintMessage("Hello, World!\n")
```

This program runs from top to bottom. But what if we want to do something more interesting?

---

## Making Decisions with IfCondition

**IfCondition** lets your program make choices. Think of it like: "If this is true, then do that."

### Basic If Statement

```ailang
age = 16

IfCondition GreaterThan(age, 13) ThenBlock: {
    PrintMessage("You are a teenager!\n")
}
```

**What's happening here?**
1. We set `age` to 16
2. We check: Is age greater than 13?
3. If YES, print the message
4. If NO, skip the message

### If with Else

What if we want to do something when the condition is false?

```ailang
age = 10

IfCondition GreaterThan(age, 13) ThenBlock: {
    PrintMessage("You are a teenager!\n")
} ElseBlock: {
    PrintMessage("You are not a teenager yet!\n")
}
```

Now the program has two paths:
- If age > 13: print "You are a teenager!"
- If age ≤ 13: print "You are not a teenager yet!"

### Multiple Conditions

You can check several things:

```ailang
temperature = 75

IfCondition GreaterThan(temperature, 80) ThenBlock: {
    PrintMessage("It's hot outside!\n")
} ElseBlock: {
    IfCondition LessThan(temperature, 60) ThenBlock: {
        PrintMessage("It's cold outside!\n")
    } ElseBlock: {
        PrintMessage("The weather is nice!\n")
    }
}
```

### Comparison Functions

Here are the comparison functions you can use:

| Function | Meaning | Example |
|----------|---------|---------|
| `EqualTo(a, b)` | Is a equal to b? | `EqualTo(5, 5)` → True |
| `NotEqual(a, b)` | Is a not equal to b? | `NotEqual(5, 3)` → True |
| `GreaterThan(a, b)` | Is a greater than b? | `GreaterThan(10, 5)` → True |
| `LessThan(a, b)` | Is a less than b? | `LessThan(3, 10)` → True |
| `GreaterEqual(a, b)` | Is a ≥ b? | `GreaterEqual(5, 5)` → True |
| `LessEqual(a, b)` | Is a ≤ b? | `LessEqual(3, 5)` → True |

### Practice: Temperature Checker

```ailang
temperature = 72

IfCondition GreaterThan(temperature, 90) ThenBlock: {
    PrintMessage("It's very hot! Stay inside!\n")
} ElseBlock: {
    IfCondition GreaterThan(temperature, 70) ThenBlock: {
        PrintMessage("Perfect weather!\n")
    } ElseBlock: {
        PrintMessage("Bring a jacket!\n")
    }
}
```

**Try changing the temperature to see different messages!**

---

## Repeating Actions with WhileLoop

**WhileLoop** repeats actions while a condition is true. Think: "While this is true, keep doing this."

### Basic Loop

```ailang
counter = 1

WhileLoop LessEqual(counter, 5) {
    PrintMessage("Count: ")
    PrintNumber(counter)
    PrintMessage("\n")
    
    counter = Add(counter, 1)
}

PrintMessage("Done counting!\n")
```

**Output:**
```
Count: 1
Count: 2
Count: 3
Count: 4
Count: 5
Done counting!
```

### How It Works

1. Check: Is counter ≤ 5?
2. If YES: Run the code inside { }
3. Go back to step 1
4. If NO: Stop looping, continue with rest of program

### Important: Don't Forget to Update!

```ailang
// BAD - Infinite loop!
counter = 1

WhileLoop LessEqual(counter, 5) {
    PrintNumber(counter)
    // Forgot to add 1 to counter!
}
```

This will print "1" forever because counter never changes!

**ALWAYS** update your counter:

```ailang
// GOOD
counter = 1

WhileLoop LessEqual(counter, 5) {
    PrintNumber(counter)
    counter = Add(counter, 1)  // Don't forget this!
}
```

### Counting Backwards

```ailang
countdown = 10

WhileLoop GreaterThan(countdown, 0) {
    PrintNumber(countdown)
    PrintMessage("... ")
    countdown = Subtract(countdown, 1)
}

PrintMessage("Blast off!\n")
```

**Output:**
```
10... 9... 8... 7... 6... 5... 4... 3... 2... 1... Blast off!
```

### Adding Numbers

```ailang
sum = 0
number = 1

WhileLoop LessEqual(number, 10) {
    sum = Add(sum, number)
    number = Add(number, 1)
}

PrintMessage("Sum of 1 to 10 is: ")
PrintNumber(sum)
PrintMessage("\n")
```

This adds: 1 + 2 + 3 + 4 + 5 + 6 + 7 + 8 + 9 + 10 = 55

---

## Choosing Paths with Fork

**Fork** is like IfCondition but **requires both paths**. You must specify what happens if true AND what happens if false.

### Basic Fork

```ailang
score = 85

Fork GreaterEqual(score, 70) TrueBlock: {
    PrintMessage("You passed!\n")
} FalseBlock: {
    PrintMessage("You need to study more.\n")
}
```

### When to Use Fork vs IfCondition

**Use IfCondition when:**
- You might not need an else block
- You want to check multiple conditions in a chain

**Use Fork when:**
- You definitely have two paths
- You want to be clear about both outcomes

### Fork Example: Even or Odd

```ailang
number = 7
remainder = Modulo(number, 2)

Fork EqualTo(remainder, 0) TrueBlock: {
    PrintNumber(number)
    PrintMessage(" is even\n")
} FalseBlock: {
    PrintNumber(number)
    PrintMessage(" is odd\n")
}
```

**How Modulo works:**
- `Modulo(7, 2)` gives the remainder when dividing 7 by 2
- 7 ÷ 2 = 3 remainder **1**
- Even numbers have remainder 0
- Odd numbers have remainder 1

---

## Multiple Choices with Branch

**Branch** lets you choose from many options, like a menu.

### Basic Branch

```ailang
day = 3

Branch day {
    Case 1: {
        PrintMessage("Monday\n")
    }
    Case 2: {
        PrintMessage("Tuesday\n")
    }
    Case 3: {
        PrintMessage("Wednesday\n")
    }
    Case 4: {
        PrintMessage("Thursday\n")
    }
    Case 5: {
        PrintMessage("Friday\n")
    }
    Default: {
        PrintMessage("Weekend!\n")
    }
}
```

### How Branch Works

1. Look at the value (day = 3)
2. Find the matching Case (Case 3)
3. Run that code
4. If no match, run Default

### Calculator Example

```ailang
operation = 2  // 1=add, 2=subtract, 3=multiply, 4=divide
a = 10
b = 3

Branch operation {
    Case 1: {
        result = Add(a, b)
        PrintMessage("Addition: ")
        PrintNumber(result)
        PrintMessage("\n")
    }
    Case 2: {
        result = Subtract(a, b)
        PrintMessage("Subtraction: ")
        PrintNumber(result)
        PrintMessage("\n")
    }
    Case 3: {
        result = Multiply(a, b)
        PrintMessage("Multiplication: ")
        PrintNumber(result)
        PrintMessage("\n")
    }
    Case 4: {
        result = Divide(a, b)
        PrintMessage("Division: ")
        PrintNumber(result)
        PrintMessage("\n")
    }
    Default: {
        PrintMessage("Unknown operation\n")
    }
}
```

### Grade Calculator

```ailang
score = 85
grade = 0

IfCondition GreaterEqual(score, 90) ThenBlock: {
    grade = 4  // A
} ElseBlock: {
    IfCondition GreaterEqual(score, 80) ThenBlock: {
        grade = 3  // B
    } ElseBlock: {
        IfCondition GreaterEqual(score, 70) ThenBlock: {
            grade = 2  // C
        } ElseBlock: {
            IfCondition GreaterEqual(score, 60) ThenBlock: {
                grade = 1  // D
            } ElseBlock: {
                grade = 0  // F
            }
        }
    }
}

Branch grade {
    Case 4: {
        PrintMessage("Excellent! You got an A!\n")
    }
    Case 3: {
        PrintMessage("Good job! You got a B!\n")
    }
    Case 2: {
        PrintMessage("You got a C.\n")
    }
    Case 1: {
        PrintMessage("You got a D. Study harder!\n")
    }
    Default: {
        PrintMessage("You failed. Keep trying!\n")
    }
}
```

---

## Loop Control

Sometimes you need to control loops in special ways.

### BreakLoop - Stop the Loop

**BreakLoop** exits a loop immediately:

```ailang
counter = 1

WhileLoop LessEqual(counter, 100) {
    PrintNumber(counter)
    PrintMessage(" ")
    
    IfCondition EqualTo(counter, 5) ThenBlock: {
        PrintMessage("\nStopping at 5!\n")
        BreakLoop
    }
    
    counter = Add(counter, 1)
}
```

**Output:**
```
1 2 3 4 5 
Stopping at 5!
```

### ContinueLoop - Skip to Next Iteration

**ContinueLoop** skips the rest of the current iteration:

```ailang
counter = 0

WhileLoop LessThan(counter, 10) {
    counter = Add(counter, 1)
    
    // Skip odd numbers
    remainder = Modulo(counter, 2)
    IfCondition EqualTo(remainder, 1) ThenBlock: {
        ContinueLoop
    }
    
    // This only prints even numbers
    PrintNumber(counter)
    PrintMessage(" ")
}
```

**Output:**
```
2 4 6 8 10
```

### Finding a Number

```ailang
target = 7
number = 1
found = 0

WhileLoop LessEqual(number, 10) {
    IfCondition EqualTo(number, target) ThenBlock: {
        PrintMessage("Found ")
        PrintNumber(target)
        PrintMessage("!\n")
        found = 1
        BreakLoop
    }
    
    number = Add(number, 1)
}

IfCondition EqualTo(found, 0) ThenBlock: {
    PrintMessage("Number not found.\n")
}
```

---

## Practice Exercises

### Exercise 1: Positive or Negative

Write a program that checks if a number is positive, negative, or zero:

```ailang
number = -5

// Your code here!
```

**Solution:**
```ailang
number = -5

IfCondition GreaterThan(number, 0) ThenBlock: {
    PrintMessage("Positive!\n")
} ElseBlock: {
    IfCondition LessThan(number, 0) ThenBlock: {
        PrintMessage("Negative!\n")
    } ElseBlock: {
        PrintMessage("Zero!\n")
    }
}
```

### Exercise 2: Count to 20

Write a program that counts from 1 to 20:

```ailang
// Your code here!
```

**Solution:**
```ailang
counter = 1

WhileLoop LessEqual(counter, 20) {
    PrintNumber(counter)
    PrintMessage(" ")
    counter = Add(counter, 1)
}

PrintMessage("\n")
```

### Exercise 3: Times Table

Print the 5 times table (5 × 1 through 5 × 10):

```ailang
// Your code here!
```

**Solution:**
```ailang
number = 1

WhileLoop LessEqual(number, 10) {
    result = Multiply(5, number)
    PrintMessage("5 × ")
    PrintNumber(number)
    PrintMessage(" = ")
    PrintNumber(result)
    PrintMessage("\n")
    
    number = Add(number, 1)
}
```

### Exercise 4: Fizz Buzz (Challenge!)

Print numbers 1 to 15, but:
- If divisible by 3, print "Fizz"
- If divisible by 5, print "Buzz"  
- If divisible by both, print "FizzBuzz"
- Otherwise, print the number

```ailang
// Your code here!
```

**Solution:**
```ailang
number = 1

WhileLoop LessEqual(number, 15) {
    div_by_3 = Modulo(number, 3)
    div_by_5 = Modulo(number, 5)
    
    IfCondition EqualTo(div_by_3, 0) ThenBlock: {
        IfCondition EqualTo(div_by_5, 0) ThenBlock: {
            PrintMessage("FizzBuzz\n")
        } ElseBlock: {
            PrintMessage("Fizz\n")
        }
    } ElseBlock: {
        IfCondition EqualTo(div_by_5, 0) ThenBlock: {
            PrintMessage("Buzz\n")
        } ElseBlock: {
            PrintNumber(number)
            PrintMessage("\n")
        }
    }
    
    number = Add(number, 1)
}
```

---

## Common Mistakes

### Mistake 1: Forgetting to Update Loop Counter

```ailang
// WRONG - Infinite loop!
counter = 1

WhileLoop LessEqual(counter, 10) {
    PrintNumber(counter)
    // Missing: counter = Add(counter, 1)
}
```

**Fix:** Always update your counter!

```ailang
// RIGHT
counter = 1

WhileLoop LessEqual(counter, 10) {
    PrintNumber(counter)
    counter = Add(counter, 1)  // Don't forget!
}
```

### Mistake 2: Wrong Comparison

```ailang
// WRONG - Won't print anything if age is exactly 13
age = 13

IfCondition GreaterThan(age, 13) ThenBlock: {
    PrintMessage("Teenager\n")
}
```

**Fix:** Use GreaterEqual if you want to include 13:

```ailang
// RIGHT
age = 13

IfCondition GreaterEqual(age, 13) ThenBlock: {
    PrintMessage("Teenager\n")
}
```

### Mistake 3: Missing ElseBlock in Fork

```ailang
// WRONG - Fork requires both blocks
Fork EqualTo(x, 5) TrueBlock: {
    PrintMessage("Five!\n")
}
// Missing FalseBlock!
```

**Fix:** Always include both blocks in Fork:

```ailang
// RIGHT
Fork EqualTo(x, 5) TrueBlock: {
    PrintMessage("Five!\n")
} FalseBlock: {
    PrintMessage("Not five!\n")
}
```

### Mistake 4: Confusing = with EqualTo

```ailang
// WRONG - This assigns, doesn't compare!
IfCondition (age = 13) ThenBlock: {
    // ...
}
```

**Fix:** Use EqualTo for comparisons:

```ailang
// RIGHT
IfCondition EqualTo(age, 13) ThenBlock: {
    // ...
}
```

---

## Next Steps

Congratulations! You now know the basics of flow control. Here's what to learn next:

### 1. Functions and SubRoutines

Learn how to organize your code into reusable pieces:

```ailang
Function.Add {
    Input: a: Integer, b: Integer
    Output: Integer
    Body: {
        result = Add(a, b)
        ReturnValue(result)
    }
}
```

### 2. Pools (Memory Management)

Learn how to store and organize data:

```ailang
FixedPool.GameScore {
    "player1": Initialize=0
    "player2": Initialize=0
    "highScore": Initialize=0
}
```

### 3. Advanced Flow Control

Once you're comfortable with the basics, try:
- Nested loops
- Complex conditions with And/Or
- Try-Catch error handling

Check out the **Advanced Flow Control Manual** when you're ready!

---

## Quick Reference

### Making Decisions

```ailang
// If-Then
IfCondition condition ThenBlock: {
    // Do this if true
}

// If-Then-Else
IfCondition condition ThenBlock: {
    // Do this if true
} ElseBlock: {
    // Do this if false
}

// Fork (must have both blocks)
Fork condition TrueBlock: {
    // True path
} FalseBlock: {
    // False path
}
```

### Repeating Actions

```ailang
// While Loop
WhileLoop condition {
    // Repeat while true
}

// Break out of loop
BreakLoop

// Skip to next iteration
ContinueLoop
```

### Multiple Choices

```ailang
// Branch
Branch value {
    Case 1: {
        // If value = 1
    }
    Case 2: {
        // If value = 2
    }
    Default: {
        // If no match
    }
}
```

### Comparisons

```ailang
EqualTo(a, b)        // a == b
NotEqual(a, b)       // a != b
GreaterThan(a, b)    // a > b
LessThan(a, b)       // a < b
GreaterEqual(a, b)   // a >= b
LessEqual(a, b)      // a <= b
```

### Math Operations

```ailang
Add(a, b)        // a + b
Subtract(a, b)   // a - b
Multiply(a, b)   // a × b
Divide(a, b)     // a ÷ b
Modulo(a, b)     // a % b (remainder)
```

---

## Keep Practicing!

The best way to learn programming is to practice. Try these challenges:

1. **Number Guessing Game**: Make a program that checks if a guess matches a secret number
2. **Multiplication Tables**: Print the complete times tables from 1 to 10
3. **Sum Calculator**: Add all numbers from 1 to 100
4. **Temperature Converter**: Convert Fahrenheit to Celsius (formula: C = (F - 32) × 5/9)

**Remember:** Every programmer makes mistakes. The important thing is to keep trying and learning from errors!

---

**Copyright © 2025 Sean Collins, 2 Paws Machine and Engineering**  
**AI Lang Compiler - Basic Flow Control Guide for Beginners**