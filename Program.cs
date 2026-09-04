using System.Text;
using SimpleLibraryOop.Events;
using SimpleLibraryOop.Models;
using SimpleLibraryOop.Services;

namespace SimpleLibraryOop;

internal class Program
{
    private static void Main()
    {
        Console.OutputEncoding = Encoding.UTF8;

        var library = new LibraryManager();

        // 訂閱事件：當 LibraryManager 發出通知時，執行這個方法。
        library.BookStatusChanged += HandleBookStatusChanged;

        AddSampleBooks(library);

        bool isRunning = true;

        while (isRunning)
        {
            ShowMenu();
            string choice = Console.ReadLine()?.Trim() ?? string.Empty;
            Console.WriteLine();

            switch (choice)
            {
                case "1":
                    ShowAllBooks(library);
                    break;
                case "2":
                    BorrowBook(library);
                    break;
                case "3":
                    ReturnBook(library);
                    break;
                case "4":
                    SearchBooks(library);
                    break;
                case "0":
                    isRunning = false;
                    Console.WriteLine("程式已結束。");
                    break;
                default:
                    Console.WriteLine("請輸入 0～4 的選項。");
                    break;
            }

            if (isRunning)
            {
                Console.WriteLine("\n按 Enter 回到主選單。");
                Console.ReadLine();
                Console.Clear();
            }
        }
    }

    private static void AddSampleBooks(LibraryManager library)
    {
        library.AddBook(new Book(1, "C# 入門練習", "王小明"));
        library.AddBook(new Book(2, "物件導向其實不難", "陳老師"));
        library.AddBook(new Book(3, "乾淨程式碼入門", "林工程師"));
    }

    private static void ShowMenu()
    {
        Console.WriteLine("============================");
        Console.WriteLine("      簡易圖書借閱系統");
        Console.WriteLine("============================");
        Console.WriteLine("1. 顯示全部書籍");
        Console.WriteLine("2. 借書");
        Console.WriteLine("3. 還書");
        Console.WriteLine("4. 搜尋書名");
        Console.WriteLine("0. 離開");
        Console.Write("請選擇功能：");
    }

    private static void ShowAllBooks(LibraryManager library)
    {
        Console.WriteLine("【全部書籍】");

        foreach (Book book in library.Books)
        {
            Console.WriteLine(book.GetDisplayText());
        }
    }

    private static void BorrowBook(LibraryManager library)
    {
        int? bookId = ReadBookId();

        if (bookId is null)
        {
            return;
        }

        Console.Write("請輸入借閱人姓名：");
        string borrowerName = Console.ReadLine()?.Trim() ?? string.Empty;

        bool success = library.BorrowBook(bookId.Value, borrowerName);

        if (!success)
        {
            Console.WriteLine("借閱失敗：請確認書籍編號、姓名，或該書是否已借出。");
        }
    }

    private static void ReturnBook(LibraryManager library)
    {
        int? bookId = ReadBookId();

        if (bookId is null)
        {
            return;
        }

        bool success = library.ReturnBook(bookId.Value);

        if (!success)
        {
            Console.WriteLine("還書失敗：請確認書籍編號，或該書是否真的已借出。");
        }
    }

    private static void SearchBooks(LibraryManager library)
    {
        Console.Write("請輸入書名關鍵字：");
        string keyword = Console.ReadLine()?.Trim() ?? string.Empty;

        List<Book> results = library.SearchByTitle(keyword).ToList();

        if (results.Count == 0)
        {
            Console.WriteLine("找不到符合的書籍。");
            return;
        }

        Console.WriteLine("\n【搜尋結果】");

        foreach (Book book in results)
        {
            Console.WriteLine(book.GetDisplayText());
        }
    }

    private static int? ReadBookId()
    {
        Console.Write("請輸入書籍編號：");
        string input = Console.ReadLine()?.Trim() ?? string.Empty;

        if (!int.TryParse(input, out int bookId))
        {
            Console.WriteLine("書籍編號必須是整數。");
            return null;
        }

        return bookId;
    }

    private static void HandleBookStatusChanged(
        object? sender,
        BookStatusChangedEventArgs eventArgs)
    {
        Console.WriteLine();
        Console.WriteLine(
            $"[事件通知 {eventArgs.OccurredAt:HH:mm:ss}] {eventArgs.Message}");
    }
}
