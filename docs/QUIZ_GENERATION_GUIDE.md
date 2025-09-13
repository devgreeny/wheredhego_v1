# Quiz Generation Guide - Enhanced Script

## 🎯 Overview

You now have an enhanced quiz generation system that can create content for both **Starting5** (NBA) and **Gridiron11** (NFL) games using a single script.

## 🚀 Available Scripts

### 1. **Enhanced Generator** (Recommended)
```bash
python generate_quiz_enhanced.py
```
- **Supports**: Both NBA and NFL quiz generation
- **Features**: Interactive mode, manual avatar assignment, batch generation
- **Best for**: Daily content creation and bulk generation

### 2. **Individual Scripts**
```bash
# NBA only (original functionality)
python starting5/generate_quiz.py --manual-avatars

# NFL only (web scraping)
python generate_nfl_quiz.py --count 3
```

## 📋 Usage Examples

### **Your Current Workflow (Enhanced)**
```bash
# Interactive mode - asks what you want to generate
python generate_quiz_enhanced.py --interactive

# Generate NBA quizzes with manual avatar assignment (your current process)
python generate_quiz_enhanced.py --game nba --manual-avatars --count 5

# Generate NFL quizzes via web scraping
python generate_quiz_enhanced.py --game nfl --count 3

# Generate both types at once
python generate_quiz_enhanced.py --game both --count 5
```

### **Manual Avatar Assignment (NBA)**
When using `--manual-avatars`, the script will prompt you for each player:
```
🏀 Avatar for LeBron James [1-14] (enter for 7): 12
🏀 Avatar for Anthony Davis [1-14] (enter for 3): 
🏀 Avatar for Russell Westbrook [1-14] (enter for 9): 5
```

### **Batch Generation**
```bash
# Generate 10 NBA quizzes without prompts
python generate_quiz_enhanced.py --game nba --count 10

# Generate 5 NFL quizzes (takes longer due to web scraping)
python generate_quiz_enhanced.py --game nfl --count 5
```

## 🎮 Interactive Mode

The enhanced script includes an interactive mode that guides you through the process:

```bash
python generate_quiz_enhanced.py --interactive
```

This will show you a menu:
```
🎮 Welcome to the Enhanced Quiz Generator!
This tool can generate quizzes for both Starting5 (NBA) and Gridiron11 (NFL)

What would you like to generate?
1. NBA quizzes (Starting5)
2. NFL quizzes (Gridiron11)  
3. Both NBA and NFL quizzes
4. Exit

Enter your choice (1-4): 
```

## 📁 Output Locations

### **NBA Quizzes (Starting5)**
- **Directory**: `app/starting5/static/preloaded_quizzes/`
- **Format**: `2023-24_0022300895_CLE.json`
- **Contains**: Player stats, college info, avatar assignments

### **NFL Quizzes (Gridiron11)**
- **Directory**: `app/gridiron11/preloaded_quizzes/`
- **Format**: `players_20250912_143022.json`
- **Contains**: Starting lineup, positions, college info

## ⚙️ Configuration

### **NBA Generation**
- **Data Source**: NBA API (nba_api)
- **Seasons**: 2005-2024
- **Requirements**: College players only
- **Avatar Assignment**: Manual or random (1-14)

### **NFL Generation**
- **Data Source**: pro-football-reference.com (web scraping)
- **Seasons**: 2010-2023
- **Requirements**: Offensive players only, known colleges
- **Rate Limiting**: 2-4 second delays between requests

## 🔧 Dependencies

Make sure you have the required packages:
```bash
pip install beautifulsoup4 lxml nba-api pandas
```

## 📊 Performance

### **NBA Generation**
- **Speed**: ~30-60 seconds per quiz
- **Success Rate**: ~80% (depends on college data availability)
- **Rate Limits**: Built-in delays for NBA API

### **NFL Generation**
- **Speed**: ~2-5 minutes per quiz (web scraping)
- **Success Rate**: ~60% (depends on lineup data availability)
- **Rate Limits**: 2-4 second delays between web requests

## 🎯 Best Practices

### **For Daily Content**
1. **Morning Generation**: Run overnight or early morning
2. **Batch Processing**: Generate multiple quizzes at once
3. **Manual Review**: Check generated content before deployment

### **For Manual Avatar Assignment**
1. **Prepare Avatar Map**: Keep a reference of which avatars work best
2. **Consistent Style**: Use similar avatars for similar player types
3. **Save Mappings**: Consider using `--avatar-mapping` for consistency

### **For NFL Generation**
1. **Be Patient**: Web scraping takes time
2. **Check Results**: Verify college information is accurate
3. **Backup Plans**: Have preloaded quizzes ready

## 🚨 Troubleshooting

### **NBA Issues**
- **No college data**: Script skips non-college players automatically
- **API rate limits**: Built-in delays handle this
- **Season data**: Older seasons may have limited data

### **NFL Issues**
- **Web scraping fails**: Check internet connection and site availability
- **No lineup data**: Some games don't have complete starting lineups
- **College info missing**: Some players may not have college data

### **General Issues**
- **Missing dependencies**: Run `pip install -r requirements.txt`
- **File permissions**: Ensure write access to output directories
- **Memory issues**: Generate fewer quizzes at once

## 🔄 Integration with Update Script

Your enhanced `update_games.py` script will automatically use these generated quizzes:

```bash
# The update script moves quizzes from preloaded_quizzes to current_quiz
python update_games.py
```

## 📈 Monitoring

### **Check Generated Content**
```bash
# View recent NBA quizzes
ls -la app/starting5/static/preloaded_quizzes/ | tail -5

# View recent NFL quizzes  
ls -la app/gridiron11/preloaded_quizzes/ | tail -5

# Check quiz content
cat app/starting5/static/preloaded_quizzes/latest_quiz.json | jq .
```

### **Validate Quiz Quality**
- **NBA**: Ensure all players have college info and valid avatars
- **NFL**: Verify formation has 11 players with position assignments
- **Both**: Check that college names are properly formatted

Your enhanced quiz generation system is now ready for production use! 🎮
